import dataclasses

from cyclopts import Parameter


@Parameter(name="*")
@dataclasses.dataclass
class Common:
    filename_prefix: str = "invoice_"
