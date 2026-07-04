#!/usr/bin/env python3
"""Export Tactile-Net to ONNX for TensorRT compilation on Jetson Orin."""

import argparse
import os
import sys

try:
    import torch
except ImportError:
    print("[!] PyTorch required: pip install -r requirements-ml.txt")
    sys.exit(1)

from tactile_net import build_tactile_net, count_parameters

ROOT = os.path.dirname(os.path.dirname(__file__))
MODELS_DIR = os.path.join(ROOT, "models")


def export_onnx(output_path: str):
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    net = build_tactile_net().eval()
    print(f"[*] Parameters: {count_parameters(net):,}")

    cap = torch.randn(1, 1, 16, 16, dtype=torch.float32)
    piezo = torch.randn(1, 1, 32, dtype=torch.float32)

    torch.onnx.export(
        net,
        (cap, piezo),
        output_path,
        input_names=["spatial_input", "temporal_input"],
        output_names=["slip_output", "delta_output"],
        dynamic_axes=None,
        opset_version=17,
    )
    print(f"[+] ONNX exported: {output_path}")
    print("[*] On Jetson: trtexec --onnx=... --saveEngine=tactile_net.engine --fp16")


def main():
    parser = argparse.ArgumentParser(description="Export Tactile-Net ONNX")
    parser.add_argument(
        "-o", "--output",
        default=os.path.join(MODELS_DIR, "tactile_net.onnx"),
    )
    args = parser.parse_args()
    export_onnx(args.output)


if __name__ == "__main__":
    main()