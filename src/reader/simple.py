import vtk
from core import Reader, Frame, PipelineInformation

class SimpleReader(Reader):
  def __init__(self, mesh:vtk.vtkDataSet):
    self.mesh = mesh

  def __aiter__(self):
    return self

  async def __anext__(self) -> Frame:
    return self.mesh

  def __len__(self) -> int:
    return 1