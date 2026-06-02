#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "numpy",
#     "pyvista",
# ]
# ///

import os
import sys
import argparse
import numpy as np
import pyvista as pv

def triangle_only(poly: pv.PolyData) -> pv.PolyData:
    """
    确保 PolyData 网格仅包含三角形面，并过滤掉多余的独立顶点和线段。
    
    参数:
        poly (pv.PolyData): 输入的网格数据
        
    返回:
        pv.PolyData: 纯三角形网格数据
    """
    # 丢弃原有的独立顶点 (verts) 和线段 (lines) 并进行三角化
    tri = poly.triangulate(pass_verts=False, pass_lines=False)
    
    # 优先尝试使用 PyVista 新版本支持的 regular_faces 属性
    try:
        if tri.is_all_triangles:
            reg_faces = tri.regular_faces
            # 在每行前添加边数 '3' 以构建符合 VTK/PyVista 格式的 faces 数组
            padding = np.full((reg_faces.shape[0], 1), 3, dtype=reg_faces.dtype)
            faces_padded = np.hstack((padding, reg_faces))
            return pv.PolyData(tri.points, faces_padded)
    except Exception:
        pass

    # 备用兼容方案：通过重塑 faces 数组过滤出标准的三角形单元
    faces = tri.faces
    if len(faces) % 4 == 0:
        try:
            faces_reshaped = faces.reshape((-1, 4))
            # 过滤出第一列标识为 3（表示三角形）的数据
            tri_faces = faces_reshaped[faces_reshaped[:, 0] == 3]
            return pv.PolyData(tri.points, tri_faces)
        except ValueError:
            pass

    return tri

def process_mesh(
    input_path: str,
    output_path: str,
    merge_points: bool = True,
    decimate: bool = True,
    reduction: float = 0.85,
    plot_result: bool = False
):
    """
    执行网格读取、清洗、三角化、简化及保存的核心逻辑。
    """
    if not os.path.exists(input_path):
        print(f"错误: 找不到输入文件 '{input_path}'", file=sys.stderr)
        sys.exit(1)

    print(f"[*] 正在读取网格文件: {input_path}")
    mesh = pv.read(input_path)

    # 确保网格类型为 PolyData
    if not isinstance(mesh, pv.PolyData):
        print("[*] 数据集非 PolyData 表面类型，正在提取外表面...")
        mesh = mesh.extract_surface()

    print(f"    - 原始顶点数: {mesh.n_points}")
    print(f"    - 原始面数: {mesh.n_faces_strict}")

    # 1. 清理网格并合并重复顶点
    if merge_points:
        print("[*] 正在合并重复顶点 (Clean)...")
        mesh = mesh.clean(tolerance=0.0)
    
    # 2. 转换并提取纯三角形网格
    print("[*] 正在执行三角化并清理非三角形面...")
    mesh = triangle_only(mesh)

    print(f"    - 清洗与三角化后顶点数: {mesh.n_points}")
    print(f"    - 清洗与三角化后面数: {mesh.n_faces_strict}")

    # 3. 减面 (网格简化)
    if decimate:
        if not (0.0 <= reduction < 1.0):
            print(f"警告: 减面比例（reduction）必须在 [0.0, 1.0) 之间，当前设定为 {reduction}。将跳过减面步骤。", file=sys.stderr)
        else:
            print(f"[*] 正在执行网格简化 (Decimate)，减面比例设定为: {reduction * 100:.1f}%")
            mesh = mesh.decimate(
                target_reduction=reduction,
                volume_preservation=False,
                attribute_error=False,
            )
            # 减面后再次过滤，确保输出结果仍为纯三角形
            mesh = triangle_only(mesh)
            print(f"    - 简化后顶点数: {mesh.n_points}")
            print(f"    - 简化后面数: {mesh.n_faces_strict}")

    # 4. 保存处理后的网格
    print(f"[*] 正在将结果保存至: {output_path}")
    mesh.save(output_path)
    print("[+] 网格处理完成。")

    # 5. 可选：渲染显示
    if plot_result:
        print("[*] 正在启动 3D 预览窗口...")
        mesh.plot()

def main():
    parser = argparse.ArgumentParser(
        description="基于 PyVista 的 3D 网格高效清理与减面简化工具",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    # 输入文件路径（位置参数）
    parser.add_argument(
        "input", 
        type=str, 
        help="输入 3D 网格模型的文件路径 (例如: mesh.obj, input.ply, input.stl)"
    )
    
    # 输出文件路径，默认 output.obj
    parser.add_argument(
        "-o", "--output", 
        type=str, 
        default="output.obj", 
        help="输出处理后的 3D 网格文件路径"
    )
    
    # 是否合并顶点（控制 merge_points），默认 True
    parser.add_argument(
        "--no-merge-points", 
        dest="merge_points", 
        action="store_false", 
        help="禁用合并重复顶点的清理操作 (默认启用)"
    )
    parser.set_defaults(merge_points=True)
    
    # 是否进行减面（控制 decimate），默认 True
    parser.add_argument(
        "--no-decimate", 
        dest="decimate", 
        action="store_false", 
        help="禁用网格简化 (减面) 操作 (默认启用)"
    )
    parser.set_defaults(decimate=True)
    
    # 减面比例，默认 0.85
    parser.add_argument(
        "-r", "--reduction", 
        type=float, 
        default=0.85, 
        help="网格简化的减面比例，范围为 [0, 1)。例如 0.85 表示移除原网格中 85%% 的面"
    )
    
    # 是否在运行完毕后可视化
    parser.add_argument(
        "--plot", 
        action="store_true", 
        help="在处理完成后启动交互式 3D 可视化窗口查看网格"
    )

    args = parser.parse_args()

    process_mesh(
        input_path=args.input,
        output_path=args.output,
        merge_points=args.merge_points,
        decimate=args.decimate,
        reduction=args.reduction,
        plot_result=args.plot
    )

if __name__ == "__main__":
    main()
