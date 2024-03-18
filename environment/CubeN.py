import torch
import torch.nn.functional as F
import numpy as np


class CubeN:
    def __init__(self, N, solveState):
        assert N in [2, 3, 4, 5], "N must be valid"
        self.N = N
        self.solveState = solveState
        self.actionsList = [
            "U",
            "U'",
            "F",
            "F'",
            "L",
            "L'",
            "D",
            "D'",
            "B",
            "B'",
            "R",
            "R'",
        ]
        self.numActions = len(self.actionsList)
        self.actions = {key: i for i, key in enumerate(self.actionsList)}

        self.state = self.getSolvedState()
        # self.solvedState = self.getSolvedState()
        self.adjIdx = self.genAdjIdx()
        self.nextStateMat = self.genNextStateMat()

    def getSolvedState(self):
        state = torch.zeros(self.N ** 2 * 6, dtype=torch.uint8)
        for i in range(6):
            state[self.N ** 2 * i: self.N ** 2 * (i + 1)] = i

        return state

    #All
    # def checkIfSolved(self, states):
    #     return torch.all(states == self.solvedState, 1)

    def checkIfSolved(self, states):
        result = []
        for state in states:
            result.append(self.checkIfSolvedSingle(state))
        return torch.tensor(result, dtype=torch.bool)


    def checkIfSolvedSingle(self, state):
        if self.solveState == 'C':
            return self.__checkIfSolvedCrossSingle(state)
        elif self.solveState == 'X':
            return self.__checkIfSolvedXCrossSingle(state)
        elif self.solveState == 'F':
            return self.__checkIfSolvedF2LSingle(state)
        else:
            print("Error Cube problem")


    # Cross -----------------------------------------------------------------------------------------------------
    def __checkIfSolvedCrossSingle(self, state):
        tmp = state.reshape(6, 3, -1)
        targetFace = tmp[3]
        # fFace = tmp[1]
        # lFace = tmp[2]
        # bFace = tmp[4]
        # rFace = tmp[5]
        surroundFaces = [tmp[1], tmp[2], tmp[4], tmp[5]]
        for face in surroundFaces:
            if face[2][1] != face[1][1]:
                return False
        return targetFace[0][1] == targetFace[1][1] == targetFace[1][0] == targetFace[1][2] == targetFace[2][1]
        return torch.equal(state, self.solvedState)
    # Cross -----------------------------------------------------------------------------------------------------


    #XCross ---------------------------------------------------------------------------------------------------
    def __checkF2L(self, face1, face2):
        if ((face1[1][1] == face1[1][0] == face1[2][0]) and 
            (face2[1][1] == face2[1][2] == face2[2][2])):
                return True 

    def __checkXCrossF2L(self, face1, face2, face3, face4):
        if self.__checkF2L(face1, face2):
            return True
        if self.__checkF2L(face2, face3):
            return True
        if self.__checkF2L(face3, face4):
            return True
        if self.__checkF2L(face4, face1):
            return True
        return False

    def __checkIfSolvedXCrossSingle(self, state):
        tmp = state.reshape(6, 3, -1)
        targetFace = tmp[3]
        surroundFaces = [tmp[1], tmp[2], tmp[4], tmp[5]]
        for face in surroundFaces:
            if face[2][1] != face[1][1]:
                return False

        if not self.__checkXCrossF2L(tmp[1], tmp[2], tmp[4], tmp[5]):
            return False
        
        return targetFace[0][1] == targetFace[1][1] == targetFace[1][0] == targetFace[1][2] == targetFace[2][1]
        # return torch.equal(state, self.solvedState)
    #XCross ---------------------------------------------------------------------------------------------------




    #F2L -----------------------------------------------------------------------------------------------------------
    def __checkAllF2L(self, faces):
        for face in faces:
            if not torch.equal(face[1], face[2]):
                return False
            centerColor = face[1][1].item()
            if not torch.all(face[1] == centerColor):
                return False
        return True

    def __checkIfSolvedF2LSingle(self, state):
        tmp = state.reshape(6, 3, -1)
        targetFace = tmp[3]
        surroundFaces = [tmp[1], tmp[2], tmp[4], tmp[5]]

        if not self.__checkAllF2L(surroundFaces):
            return False

        return torch.all(targetFace == 3).item()
    #F2L -----------------------------------------------------------------------------------------------------------



    def doAction(self, action, state=None):
        assert action in self.actions

        if state is None:
            state = self.state

        state = state[self.nextStateMat[self.actions[action]]]

        return state

    def genNextStateMat(self):
        solvedCube = np.arange(self.N ** 2 * 6)

        nextStateMat = np.tile(solvedCube, (len(self.actions), 1))

        for actIndex in range(len(self.actions)):
            # Rotate Face
            # faceToRotate 0: U, 1: F, 2: L, 3: D, 4: B, 5: R

            faceToRotate = actIndex // 2

            rotatedCube = solvedCube.copy()

            face = np.arange(
                faceToRotate * self.N ** 2, (faceToRotate + 1) * self.N ** 2
            ).reshape(self.N, self.N)

            adjPieces = rotatedCube[self.adjIdx[faceToRotate]]

            if actIndex % 2 == 0:
                rotatedFace = np.rot90(face, 3)
                adjPieces = np.roll(adjPieces, self.N)
            else:
                rotatedFace = np.rot90(face, 1)
                adjPieces = np.roll(adjPieces, -self.N)

            rotatedCube[
                faceToRotate * self.N ** 2: (faceToRotate + 1) * self.N ** 2
            ] = rotatedFace.flatten()

            rotatedCube[self.adjIdx[faceToRotate]] = adjPieces
            nextStateMat[actIndex] = rotatedCube

        return torch.tensor(nextStateMat, dtype=torch.int64)

    def genAdjIdx(self):
        adjIdx = np.zeros((6, 4 * self.N), dtype=int)
        multiIdx = []
        for i in range(6):
            faces = [(i + j) % 6 for j in range(6) if j not in [0, 3]]
            if i % 2:
                faces = [faces[0]] + faces[1:][::-1]
            faces = np.array(faces).repeat(self.N)

            if i == 0:  # U
                # F L B R
                positionsRow = np.zeros(4 * self.N)
                positionsCol = np.tile(np.arange(self.N - 1, -1, -1), 4)

            if i == 1:  # F

                # L U R D
                positionsRow = np.array(
                    [
                        np.arange(self.N - 1, -1, -1),  # L
                        np.ones(self.N) * (self.N - 1),  # U
                        np.arange(self.N),  # R
                        np.zeros(self.N),  # D
                    ]
                )
                positionsCol = np.array(
                    [
                        np.ones(self.N) * (self.N - 1),  # L
                        np.arange(self.N),  # U
                        np.zeros(self.N),  # R
                        np.arange(self.N - 1, -1, -1),  # D
                    ]
                )
            if i == 2:  # L
                # D B U F
                positionsRow = np.array(
                    [
                        np.arange(self.N),  # D
                        np.arange(self.N - 1, -1, -1),  # B
                        np.arange(self.N),  # U
                        np.arange(self.N),  # F
                    ]
                )
                positionsCol = np.array(
                    [
                        np.zeros(self.N),  # D
                        np.ones(self.N) * (self.N - 1),  # B
                        np.zeros(self.N),  # U
                        np.zeros(self.N),  # F
                    ]
                )

            if i == 3:  # D
                # B L F R
                positionsRow = positionsRow = np.ones(
                    4 * self.N) * (self.N - 1)
                positionsCol = positionsCol = np.tile(np.arange(self.N), 4)

            if i == 4:  # B
                # R U L D
                positionsRow = np.array(
                    [
                        np.arange(self.N - 1, -1, -1),  # R
                        np.zeros(self.N),  # U
                        np.arange(self.N),  # L
                        np.ones(self.N) * (self.N - 1),  # D
                    ]
                )
                positionsCol = np.array(
                    [
                        np.ones(self.N) * (self.N - 1),  # R
                        np.arange(self.N - 1, -1, -1),  # U
                        np.zeros(self.N),  # L
                        np.arange(self.N),  # D
                    ]
                )
            if i == 5:  # R
                # U B D F

                positionsRow = np.array(
                    [
                        np.arange(self.N - 1, -1, -1),  # U
                        np.arange(self.N),  # B
                        np.arange(self.N - 1, -1, -1),  # D
                        np.arange(self.N - 1, -1, -1),  # F
                    ]
                )
                positionsCol = np.array(
                    [
                        np.ones(self.N) * (self.N - 1),  # U
                        np.zeros(self.N),  # B
                        np.ones(self.N) * (self.N - 1),  # D
                        np.ones(self.N) * (self.N - 1),  # F
                    ]
                )
            positionsRow = positionsRow.flatten()
            positionsCol = positionsCol.flatten()

            multiIdx = np.stack(
                (faces.astype(int), positionsRow.astype(
                    int), positionsCol.astype(int))
            )

            adjIdx[i] = np.ravel_multi_index(multiIdx, (6, self.N, self.N))

        return adjIdx

    def nextState(
        self, states, actions,
    ):
        return states.gather(
            1, self.nextStateMat.index_select(0, torch.as_tensor(actions)),
        )

    def generateScramble(self, noMoves):
        scramble = np.random.randint(0, self.numActions, noMoves)
        state = self.solvedState.clone()

        for move in scramble:
            state = self.doAction(self.actionsList[move], state)

        return state

    def generateScrambles(self, numStates, maxScrambles, minScrambles=0):

        states = self.solvedState.repeat(numStates, 1)
        scrambleNums = np.random.randint(
            minScrambles, maxScrambles + 1, numStates)
        numMoves = np.zeros(numStates)

        while np.max(numMoves < scrambleNums):

            poses = np.where((numMoves < scrambleNums))[0]

            subsetSize = max(len(poses) // self.numActions, 1)

            poses = np.random.choice(poses, subsetSize)

            move = np.random.randint(0, self.numActions)
            states[poses] = self.nextState(states[poses], [move] * subsetSize)
            numMoves[poses] += 1

        return states

    def exploreNextStates(self, states):

        validStates = torch.tensor(
            [True] * self.numActions).repeat(states.shape[0], 1)

        nextStates = states.repeat_interleave(self.numActions, dim=0).gather(
            1,
            self.nextStateMat.index_select(
                0,
                torch.as_tensor(
                    np.tile(
                        np.arange(0, self.numActions,
                                  dtype=np.int64), states.shape[0],
                    ),
                ),
            ),
        )

        nextStates = nextStates.view(states.shape[0], self.numActions, -1)

        goals = self.checkIfSolved(nextStates.view(-1, self.N ** 2 * 6)).view(
            -1, self.numActions
        )

        return nextStates, validStates, goals

    def NextStateSpotToAction(self, i):
        return self.actionsList[i]

    @staticmethod
    def oneHotEncoding(states):
        return F.one_hot(states.view(-1).long(), 6).view(-1, states.shape[1]*6)

