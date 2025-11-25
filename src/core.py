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