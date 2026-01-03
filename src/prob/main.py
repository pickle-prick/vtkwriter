import os
import vtk
import sys

# Path to the directory containing the .pyd file
pyd_dir_win = os.path.abspath(os.path.join(os.path.dirname(__file__), "."))
pyd_dir_linux = os.path.abspath(os.path.join(os.path.dirname(__file__), "."))

# 1. Add to sys.path so Python can find the module to import
if pyd_dir_win not in sys.path:
    sys.path.append(pyd_dir_win)
if pyd_dir_linux not in sys.path:
    sys.path.append(pyd_dir_linux)

# 2. Add to DLL directory so Windows can find dependent DLLs (if any)
if os.name == "nt":
    os.add_dll_directory(pyd_dir_win)

import typedsender  # noqa: E402
import time  # noqa: E402
import sys  # noqa: E402


def main():
    print("=== Python Demo Server ===")

    generator = typedsender.SchemaGenerator()
    generator.set_schema_info("DemoSchema", "Demo Schema Description", 1, 0, 0)
    generator.add_vector_def(1, "vec_dynamic", "Dynamic length vector", 0, [])
    generator.add_vector_def(2, "vec_1", "Length 1 vector", 1, [0.0])
    generator.add_vector_def(3, "speed_vec", "a vec3 for speed", 3, [0.0, 0.0, 0.0])
    generator.add_trimesh_def(
        4,
        "simple_mesh",
        "A simple triangle mesh",
        [(0, 0, 0), (1, 0, 0), (0, 1, 0)],
        [(0, 1, 2)],
        [("stress", "stress desc"), ("strain", "strain desc")],
    )
    generator.add_namedtuple_def(
        5,
        "point_data",
        "Point data with named fields",
        [("temperature", "temperature desc"), ("pressure", "pressure desc")],
        [20.0, 1.0],
    )
    sig, schema_buffer = generator.build_schema_buffer()

    print("Schema Signature:", sig.hex())

    manager = typedsender.SenderManager(schema_buffer)

    transport = typedsender.ZMQResTransport("tcp://*:5555")
    transport.set_on_client_connected(lambda: print("Client connected!"))

    manager.set_transport(transport)

    sender_dyn = manager.get_vector_sender(1, 0)
    sender_1 = manager.get_vector_sender(2, 1)
    sender_3 = manager.get_vector_sender(3, 3)
    trimesh_sender = manager.get_trimesh_sender(4)
    namedtuple_sender = manager.get_namedtuple_sender(5, ["temperature", "pressure"])

    transport.session_begin()
    manager.session_initializing(1)

    sender_dyn.send_init([])
    sender_1.send_init([1.0])
    sender_3.send_init([1.0, 2.0, 3.0])
    trimesh_sender.send_init({"stress": [0.0, 0.0, 0.0], "strain": [0.0, 0.0, 0.0]})

    manager.session_initialized()

    frame_count = 0
    try:
        for _ in range(20):
            t = frame_count * 0.1

            dyn_data = [t] * (frame_count % 10 + 1)
            sender_dyn.send_frame(t, dyn_data)

            sender_1.send_frame(t, [t])
            sender_3.send_frame(t, [t, t * 2, t * 3])
            trimesh_sender.send_frame(
                t,
                {
                    "stress": [t * 0.1, t * 0.2, t * 0.3],
                    "strain": [t * 0.01, t * 0.02, t * 0.03],
                },
            )
            namedtuple_sender.send_frame(
                t,
                {
                    "temperature": 20.0 + t,
                    "pressure": 1.0 + t * 0.1,
                },
            )

            print(f"Sent frame {frame_count}")
            frame_count += 1
            time.sleep(0.01)
    except KeyboardInterrupt:
        print("Stopping...")

    transport.session_end()
    transport.stop()


if __name__ == "__main__":
    main()
