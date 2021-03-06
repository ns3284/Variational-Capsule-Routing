import torch
import numpy as np
import torch.nn as nn
import torch.nn.functional as F

from layers import *
from vb_routing import *

class CapsuleNet(nn.Module):
    ''' Example: Simple 1 layer CapsNet '''
    def __init__(self, args):
        super(CapsuleNet, self).__init__()

        self.P = args.pose_dim
        self.D = int(np.max([2, self.P*self.P]))
        self.A, self.B = args.arch[0], args.arch[1]
        self.n_classes = args.n_classes = args.arch[-1]
        self.in_channels = args.n_channels

        self.Conv_1 = nn.Conv2d(in_channels=self.in_channels, out_channels=self.A,
            kernel_size=5, stride=2, bias=False)
        nn.init.kaiming_uniform_(self.Conv_1.weight)
        self.BN_1 = nn.BatchNorm2d(self.A)

        self.PrimaryCaps = PrimaryCapsules2d(in_channels=self.A, out_caps=self.B,
            kernel_size=3, stride=2, pose_dim=self.P)

        # self.ClassCaps = ConvCapsules2d(in_caps=self.B, out_caps=self.n_classes,
        #     kernel_size=1, stride=1, pose_dim=self.P, share_W_ij=True, coor_add=True)

        # same as dense caps, no weights are shared between class_caps
        self.ClassCaps = ConvCapsules2d(in_caps=self.B, out_caps=self.n_classes,
            kernel_size=6, stride=1, pose_dim=self.P) # K=5 for (28,28), K=6 for (32,32), K=8 for (40,40)

        self.ClassRouting = VariationalBayesRouting2d(in_caps=self.B, out_caps=self.n_classes,
            cov='diag', pose_dim=self.P, iter=args.routing_iter,
            alpha0=1., m0=torch.zeros(self.D), kappa0=1.,
            Psi0=torch.eye(self.D), nu0=self.D+1, class_caps=True)

    def forward(self, x):

        # Out ← [?, A, F, F]
        x = F.relu(self.BN_1(self.Conv_1(x)))

        # Out ← a [?, B, F, F], v [?, B, P, P, F, F]
        a,v = self.PrimaryCaps(x)

        # Out ← a [?, B, 1, 1, 1, F, F, K, K], v [?, B, C, P*P, 1, F, F, K, K]
        a,v = self.ClassCaps(a,v)

        # Out ← yhat [?, C], v [?, C, P*P, 1]
        yhat, v = self.ClassRouting(a,v)

        return yhat
