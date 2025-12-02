from dataclasses import dataclass
from abc import ABC, abstractmethod
import vtk
import typing as t

@dataclass
class PipelineInformation:
  total_frame_count:int
  total_frame_duration_ms:int

@dataclass
class Frame:
  pipeline_info:PipelineInformation
  frame_index:int
  frame_time:float
  dataset:vtk.vtkDataSet

class Reader(ABC):
  @abstractmethod
  def __len__(self) -> int:
    pass

  @abstractmethod
  def __aiter__(self):
    pass

  @abstractmethod
  async def __anext__(self) -> Frame:
    pass

################################
## Writer

@dataclass
class Message:
  kind:str
  timestamp:float
  payload:bytes
  payload_size:int

class Writer(ABC):
  def __len__(self) -> int:
    pass

  def has_any(self) -> bool:
    pass

  def dock(port:int) -> None:
    pass

  def undock(port:int) -> None:
    pass

  # queue
  def push_back(msg: Message) -> None:
    pass

  # stack
  def push_front(msg: Message) -> None:
    pass

  def override(msg: Message) -> None:
    pass

  def eof(msg: Message) -> None:
    pass

  def capture(self, count:int) -> some:
    pass

  def capture_and_save(self, count:int, out_file:str) -> None:
    pass
