import torch.nn as nn


def getNetwork(networkType, size) -> nn.Module:
    if networkType == "simple":
        from networks.CubeNetSimple import CubeNet

        return CubeNet(size)
    elif networkType == "residual":
        from networks.CubeNetRes import CubeNet

        return CubeNet(size)
    elif networkType == "paper":
        from networks.CubeNetPaper import CubeNet

        return CubeNet(size)
    else:
        raise ValueError("Invalid Network Type")
