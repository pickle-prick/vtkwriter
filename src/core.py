from dataclasses import dataclass
from abc import ABC, abstractmethod
import vtk
import typing as t
from enum import Enum

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

class MessageAction(Enum):
  Invalid   = -1
  Dock      = 0
  UnDock    = 1
  PushBack  = 2
  PushFront = 3
  Override  = 4
  EOF       = 5

class MessageKind(Enum):
  Invalid   = -1
  VtkFrame  = 0
  Table     = 1
  Image     = 2
  Log       = 3

@dataclass
class Message:
  action:MessageAction
  kind:MessageKind
  timestamp:float
  payload:bytes

class Writer(ABC):
  @abstractmethod
  def __len__(self) -> int:
    pass

  @abstractmethod
  def __aiter__(self):
    pass

  @abstractmethod
  async def __anext__(self) -> Frame:
    pass

  @abstractmethod
  def has_any(self) -> bool:
    pass

  @abstractmethod
  def dock(port:int) -> None:
    # FIXME: we could query the port info while docking
    pass

  @abstractmethod
  def undock(port:int) -> None:
    pass

  # queue
  @abstractmethod
  def push_back(msg: Message) -> None:
    pass

  # stack
  @abstractmethod
  def push_front(msg: Message) -> None:
    pass

  @abstractmethod
  def override(msg: Message) -> None:
    pass

  @abstractmethod
  def eof(msg: Message) -> None:
    pass

  @abstractmethod
  def capture(self, count:int) -> t.List[Message]:
    pass

  @abstractmethod
  def capture_and_save(self, count:int, out_file:str) -> None:
    pass
