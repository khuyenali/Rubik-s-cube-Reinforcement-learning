import numpy as np
import torch
import pycuber as pc
import config.config as config
# import argparse
# import os

from flask import Flask, render_template, jsonify, request
from flask_cors import CORS, cross_origin

from search.BWAS import batchedWeightedAStarSearch
from environment.CubeN import CubeN
from networks.getNetwork import getNetwork

from pycuber.solver.cfop.oll import OLLSolver
from pycuber.solver.cfop.pll import PLLSolver

app = Flask(__name__)
cors = CORS(app)
app.config["CORS_HEADERS"] = "Content-Type"

colorToNum = {
    "r": 2,
    "y": 0,
    "g": 1,
    "w": 3,
    "o": 5,
    "b": 4,
}

# colorToNum = {
#         "r": 0,
#         "y": 1,
#         "g": 2,
#         "w": 3,
#         "o": 4,
#         "b": 5,
# }


def converToState(cube: pc.Cube):
    state = []
    for face in "UFLDBR":
        face = cube.get_face(face)
        for row in face:
            for color in row:
                # state.append(int(str(color)))
                print(color)
                state.append(colorToNum[str(color)[1]])
    state = np.array(state)
    return state

cube = pc.Cube()
# cube(moves)
converToState(cube)


cube = pc.Cube()

conf3 = config.Config("config/cube3.ini")

# loadPathThreeCross = args.threeNetCross
# loadPathThreeF2L = args.threeNetF2L

# if not os.path.isfile(loadPathThreeCross):
#     raise ValueError("No 3x3 Network Saved in this Path")

# if not os.path.isfile(loadPathThreeF2L):
#     raise ValueError("No 3x3 Network Saved in this Path")

env3 = CubeN(3, "C")
net3C = getNetwork("paper", 3)
net3F = getNetwork("paper", 3)
net3X = getNetwork("paper", 3)

device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
print("device: ", device)

net3C.to(device)
net3F.to(device)
net3X.to(device)

net3C.load_state_dict(torch.load("saves/CrossNetwork.pt"))
net3C.eval()

net3F.load_state_dict(torch.load("saves/F2LnNetwork.pt"))
net3F.eval()

net3X.load_state_dict(torch.load("saves/XCrossNetwork.pt"))
net3X.eval()


@app.route("/")
@cross_origin()
def main():
    return render_template("index.html")


@app.route("/auto", methods=["GET"])
@cross_origin()
def auto():
    scramMoves = pc.Formula().random()
    # print(type(scramMoves))
    return jsonify(str(scramMoves))


@app.route("/move", methods=["POST"])
@cross_origin()
def move():
    request_data = request.get_json()
    moves = request_data["moves"]

    cube = pc.Cube()
    cube(moves)
    scrambleNumpy = converToState(cube)

    scramble = torch.tensor(scrambleNumpy, dtype=torch.uint8)
    env3.solveState = "X"
    # print(scramble)
    (
        moves,
        _,
        _,
        isSolved,
        solveTime,
    ) = batchedWeightedAStarSearch(
        scramble,
        conf3.depthWeight,
        conf3.numParallel,
        env3,
        net3C,
        device,
        300,
    )

    if isSolved and len(moves) < 12:
        crossResponse = {
            "done": isSolved,
            "time": solveTime,
            "moves": moves,
            "movesCount": len(moves) if isSolved else -1,
            "session": "XCross",
        }
    else:
        session = "Cross"
        env3.solveState = "C"
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
            "session": "Cross",
        }

    cube(" ".join(moves))
    scrambleNumpy = converToState(cube)
    scramble = torch.tensor(scrambleNumpy, dtype=torch.uint8)
    # print(scramble)
    env3.solveState = "F"
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
        "session": "F2L",
    }

    if not isSolved:
        return jsonify({"cross": crossResponse, "f2l": f2lResponse})

    cube(" ".join(moves))
    oSolver = OLLSolver(cube)
    ollMoves = str(oSolver.solve())

    pSolder = PLLSolver(cube)
    pllMoves = str(pSolder.solve())

    response = {
        "cross": crossResponse,
        "f2l": f2lResponse,
        "oll": {"moves": ollMoves, "movesCount": len(ollMoves.split())},
        "pll": {"moves": pllMoves, "movesCount": len(pllMoves.split())},
    }
    return jsonify(response)


if __name__ == "__main__":
    pass
    # app.run(host="0.0.0.0", debug=True)
