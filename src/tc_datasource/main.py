import os
import sys
import math

# Path to the directory containing the .pyd file
pyd_dir_win = os.path.abspath(os.path.join(os.path.dirname(__file__), "py/Release"))
if pyd_dir_win not in sys.path:
  sys.path.append(pyd_dir_win)

if os.name == "nt":
  os.add_dll_directory(pyd_dir_win)

import typedsender  # noqa: E402
import time  # noqa: E402
import sys  # noqa: E402

def build_schema():
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

def main():
  print("=== Python Demo Server ===")

  # FIXME: load schema_buffer here
  schema_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "20.scb"))
  with open(schema_path, "rb") as f:
    schema_buffer = f.read()

  manager = typedsender.SenderManager(schema_buffer)
  transport = typedsender.ZMQResTransport("tcp://*:5554")
  transport.set_on_client_connected(lambda: print("Client connected!"))

  manager.set_transport(transport)

  # Load sender
  # FIXME
  tcp_x_sender = manager.get_namedtuple_sender(55, ["value"])
  tcp_y_sender = manager.get_namedtuple_sender(56, ["value"])
  tcp_z_sender = manager.get_namedtuple_sender(57, ["value"])

  torque_1_x_sender = manager.get_namedtuple_sender(67, ["value"]);
  torque_1_y_sender = manager.get_namedtuple_sender(68, ["value"]);
  torque_1_z_sender = manager.get_namedtuple_sender(69, ["value"]);
  torque_2_x_sender = manager.get_namedtuple_sender(70, ["value"]);
  torque_2_y_sender = manager.get_namedtuple_sender(71, ["value"]);
  torque_2_z_sender = manager.get_namedtuple_sender(72, ["value"]);
  # namedtuple_sender = manager.get_namedtuple_sender(0, [])

  transport.session_begin()
  manager.session_initializing(1)

  # tcp_x_sender.send_init({"value": 0})
  # tcp_y_sender.send_init({"value": 0})
  # tcp_z_sender.send_init({"value": 0})

  manager.session_initialized()

  # Send Frames 
  for i in range(300):
    t = 0.1*i

    tcp_x_sender.send_frame(t, {"value": math.sin(t)*1})
    tcp_y_sender.send_frame(t, {"value": math.sin(t)*0.5})
    tcp_z_sender.send_frame(t, {"value": math.sin(t)*0.2})

    torque_1_x_sender.send_frame(t, {"value": 1.2 * math.sin(t)})
    torque_1_y_sender.send_frame(t, {"value": 0.7 * math.sin(1.7 * t + 0.8)})
    torque_1_z_sender.send_frame(t, {"value": 0.4 + 0.9 * math.cos(0.6 * t + 1.1)})

    torque_2_x_sender.send_frame(t, {"value": 2.0 * math.sin(0.9 * t + 0.3)})
    torque_2_y_sender.send_frame(t, {"value": -1.3 + 1.6 * math.cos(1.4 * t)})
    torque_2_z_sender.send_frame(t, {"value": 1.1 * math.sin(2.2 * t + 2.0)})

    print(f"{i} sent")
    time.sleep(1);

  transport.session_end()
  transport.stop()

if __name__ == "__main__":
  main()
