import numpy as np
import torch
import pycuber as pc
import config.config as config
import argparse
import os

from flask import Flask, render_template, jsonify, request
from flask_cors import CORS, cross_origin

from search.BWAS import batchedWeightedAStarSearch
from environment.CubeN import CubeN
from networks.getNetwork import getNetwork

from pycuber.solver.cfop.oll import OLLSolver
from pycuber.solver.cfop.pll import PLLSolver

app = Flask(__name__)
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'


def converToState(cube):
    state = []
    for face in 'UFLDBR':
        face = cube.get_face(face)
        for row in face:
            for color in row:
                state.append(int(str(color)))
    state = np.array(state)
    return state


cube = pc.Cube()
# scramMoves = pc.formula.Formula().random()
# cube(scramMoves)
# print(scramMoves)

# scrambleNumpy = converToState(cube)
# print(scrambleNumpy)

argParser = argparse.ArgumentParser()
argParser.add_argument(
    "-nc", "--threeNetCross", required=True, help="Path of 3x3 Network", type=str
)
argParser.add_argument(
    "-nf", "--threeNetF2L", required=True, help="Path of 3x3 Network", type=str
)
argParser.add_argument(
    "-c3", "--configThree", help="3x3 Config File", type=str
)

args = argParser.parse_args()

conf3 = config.Config(args.configThree)

loadPathThreeCross = args.threeNetCross
loadPathThreeF2L = args.threeNetF2L

if not os.path.isfile(loadPathThreeCross):
    raise ValueError("No 3x3 Network Saved in this Path")

if not os.path.isfile(loadPathThreeF2L):
    raise ValueError("No 3x3 Network Saved in this Path")

env3 = CubeN(conf3.puzzleSize, 'C')
net3C = getNetwork(conf3.puzzle, conf3.networkType)(conf3.puzzleSize)
net3F = getNetwork(conf3.puzzle, conf3.networkType)(conf3.puzzleSize)
# net3X = getNetwork('cubeN', 'paper')(3)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

net3C.to(device)
net3F.to(device)
# net3X.to(device)

net3C.load_state_dict(torch.load(loadPathThreeCross))
net3C.eval()

net3F.load_state_dict(torch.load(loadPathThreeF2L))
net3F.eval()

# net3X.load_state_dict(torch.load("saves/XCrossNetwork.pt"))
# net3X.eval()

@app.route("/")
@cross_origin()
def main():
    return render_template('index.html')


@app.route("/auto", methods=['GET'])
@cross_origin()
def auto():
    scramMoves = pc.formula.Formula().random()
    # print(type(scramMoves))
    return jsonify(str(scramMoves))


@app.route('/move', methods=['POST'])
@cross_origin()
def move():
    session = "Cross"
    request_data = request.get_json()
    moves = request_data['moves']

    cube = pc.Cube()
    cube(moves)
    scrambleNumpy = converToState(cube)

    scramble = torch.tensor(scrambleNumpy, dtype=torch.uint8)
    env3.solveState = 'C'
    # print(scramble)
    (
        moves,
        numNodesGenerated,
        searchItr,
        isSolved,
        solveTime,
    ) = batchedWeightedAStarSearch(
        scramble,
        conf3.depthWeight,
        conf3.numParallel,
        env3,
        net3C,
        device,
        conf3.maxSearchItr,
    )

    # print("Solve:", moves)
    crossResponse = {
        "done": isSolved,
        "time": solveTime,
        "moves": moves,
        "movesCount": len(moves) if isSolved else -1,
        "session": "Cross"
    }

    cube(" ".join(moves))
    scrambleNumpy = converToState(cube)
    scramble = torch.tensor(scrambleNumpy, dtype=torch.uint8)
    # print(scramble)
    env3.solveState = 'F'
    (
        moves,
        numNodesGenerated,
        searchItr,
        isSolved,
        solveTime,
    ) = batchedWeightedAStarSearch(
        scramble,
        conf3.depthWeight,
        conf3.numParallel,
        env3,
        net3F,
        device,
        conf3.maxSearchItr,
    )

    # print("Solve:", moves)
    f2lResponse = {
        "done": isSolved,
        "time": solveTime,
        "moves": moves,
        "movesCount": len(moves) if isSolved else -1,
        "session": "F2L"
    }

    if not isSolved:
        return jsonify({
            "cross": crossResponse,
            "f2l": f2lResponse
        })

    cube(" ".join(moves))
    oSolver = OLLSolver(cube)
    ollMoves = str(oSolver.solve())

    pSolder = PLLSolver(cube)
    pllMoves = str(pSolder.solve())

    response = {
        "cross": crossResponse,
        "f2l": f2lResponse,
        "oll":{
            "moves": ollMoves,
            "movesCount": len(ollMoves.split())
        },
        'pll':{
            "moves": pllMoves,
            "movesCount": len(pllMoves.split())
        }
    }
    return jsonify(response)


if __name__ == "__main__":
    app.run(debug=True)
    
