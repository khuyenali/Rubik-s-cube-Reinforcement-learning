import time
import torch
from heapq import heappop, heappush
from search.node import Node
import inspect


def convertTostandardMoves(moves):
    standardMoves = []
    i = 0
    while i < (len(moves) - 1):
        if moves[i] == moves[i + 1]:
            if len(moves[i]) == 2:
                standardMoves.append(moves[i][0] + "2")
            else:
                standardMoves.append(moves[i] + "2")
            i += 1
        else:
            standardMoves.append(moves[i])

        i += 1

    return standardMoves


def batchedWeightedAStarSearch(
    scramble,
    depthWeight,
    numParallel,
    env,
    heuristicFn,
    device,
    maxSearchItr,
    verbose=False,
):
    if not inspect.ismethod(heuristicFn):
        heuristicFn.to(device)

    openNodes = []
    closedNodes = dict()

    root = Node(scramble, None, None, 0, 0, env.checkIfSolvedSingle(scramble))
    heappush(openNodes, (root.cost, id(root), root))
    closedNodes[hash(root)] = root

    searchItr = 1
    numNodesGenerated = 1
    isSolved = False

    startTime = time.time()
    solvedNode = None

    with torch.no_grad():
        while not isSolved and searchItr <= maxSearchItr:

            startIterTime = time.time()

            numGet = min(len(openNodes), numParallel)
            currNodes = []

            for _ in range(numGet):
                node = heappop(openNodes)[2]
                currNodes.append(node)
                if node.isSolved:
                    isSolved = True
                    solvedNode = node

            currStates = [node.state for node in currNodes]
            currStates = torch.stack(currStates)

            childrenStates, valChildrenStates, goalChildren = env.exploreNextStates(
                currStates
            )

            children = []
            depths = []

            for i in range(len(currNodes)):
                parent = currNodes[i]
                for j in range(len(childrenStates[i])):
                    if valChildrenStates[i][j]:
                        action = env.NextStateSpotToAction(j)
                        depths.append(parent.depth + 1)
                        children.append(
                            Node(
                                childrenStates[i][j],
                                parent,
                                action,
                                parent.depth + 1,
                                0,
                                goalChildren[i][j],
                            )
                        )

            nodesToAddIdx = []

            for i, child in enumerate(children):
                if hash(child) in closedNodes:
                    if closedNodes[hash(child)].depth > child.depth:
                        found = closedNodes.pop(hash(child))
                        found.depth = child.depth
                        found.parent = child.parent
                        found.parentMove = child.parentMove
                        children[i] = found
                        nodesToAddIdx.append(i)
                else:
                    closedNodes[hash(child)] = child
                    nodesToAddIdx.append(i)

            children = [children[i] for i in nodesToAddIdx]
            depths = torch.tensor([depths[i] for i in nodesToAddIdx])

            childrenStates = childrenStates[valChildrenStates][nodesToAddIdx]

            if not inspect.ismethod(heuristicFn):
                childrenStates = env.oneHotEncoding(childrenStates).to(device)

            hValue = heuristicFn(childrenStates).cpu()

            bestHValue = 0
            if hValue.nelement() > 0:
                bestHValue = min(hValue)

            costs = hValue + depthWeight * depths

            for cost, child in zip(costs, children):
                child.cost = cost
                heappush(openNodes, (child.cost, id(child), child))

            numNodesGenerated += len(children)
            if verbose:
                print(
                    "Search Itr: %i | Best H Value: %.2f | Iteration time: %.2f seconds"
                    % (searchItr, bestHValue, time.time() - startIterTime),
                    flush=True,
                )

            searchItr += 1

    searchTime = time.time() - startTime

    moves = []
    if isSolved:
        node = solvedNode

        if node != None:
            while node.depth > 0:
                moves.append(node.parentMove)
                node = node.parent
            moves = moves[::-1]

    else:
        moves = None

    if moves:
        convertTostandardMoves(moves)
    return moves, numNodesGenerated, searchItr, isSolved, searchTime
