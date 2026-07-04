#!/usr/bin/env python3
"""
Tactile-Net — corrected multi-modal fusion model for QCTB CIC.
Spatial 16×16 capacitive + temporal 32-sample piezo → slip + grip delta.
"""

from __future__ import annotations

try:
    import torch
    import torch.nn as nn
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


def build_tactile_net():
    if not TORCH_AVAILABLE:
        raise ImportError("PyTorch required: pip install torch (see requirements-ml.txt)")

    class TactileNet(nn.Module):
        def __init__(self):
            super().__init__()
            self.spatial = nn.Sequential(
                nn.Conv2d(1, 16, kernel_size=3, stride=1, padding=1),
                nn.ReLU(inplace=True),
                nn.Conv2d(16, 32, kernel_size=3, stride=2, padding=1),
                nn.ReLU(inplace=True),
                nn.AdaptiveAvgPool2d((4, 4)),
            )
            self.temporal = nn.Sequential(
                nn.Conv1d(1, 8, kernel_size=3, stride=1, padding=1),
                nn.ReLU(inplace=True),
                nn.Conv1d(8, 16, kernel_size=3, stride=2, padding=1),
                nn.ReLU(inplace=True),
                nn.Conv1d(16, 16, kernel_size=3, stride=2, padding=1),
                nn.ReLU(inplace=True),
            )
            self.fusion = nn.Sequential(
                nn.Linear(512 + 128, 64),
                nn.ReLU(inplace=True),
                nn.Linear(64, 2),
            )

        def forward(self, spatial_input, temporal_input):
            s = self.spatial(spatial_input)
            s = s.view(s.size(0), -1)
            t = self.temporal(temporal_input)
            t = t.view(t.size(0), -1)
            fused = torch.cat([s, t], dim=1)
            out = self.fusion(fused)
            slip = torch.sigmoid(out[:, 0:1])
            delta = out[:, 1:2]
            return slip, delta

    return TactileNet()


def count_parameters(model) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


if __name__ == "__main__":
    if not TORCH_AVAILABLE:
        print("[!] Install torch: pip install -r requirements-ml.txt")
        raise SystemExit(1)
    net = build_tactile_net()
    n = count_parameters(net)
    print(f"TactileNet parameters: {n:,} ({'OK' if n < 150_000 else 'OVER LIMIT'})")
    cap = torch.randn(1, 1, 16, 16)
    piezo = torch.randn(1, 1, 32)
    slip, delta = net(cap, piezo)
    print(f"slip={slip.item():.4f} delta={delta.item():.4f}")