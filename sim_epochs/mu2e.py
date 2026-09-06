"""Everything sim-epochs needs from Mu2e conventions, in one place:
the dot-name grammar, the cnf jobdef tarball, four SAM calls, and the
SAM-location-to-path rule. Cut from prodtools 2026-09-05; see docs/design.md section 21."""
import json
import os
import re
import tarfile
from functools import lru_cache
from typing import List, Optional

from samweb_client import SAMWebClient  # type: ignore
from samweb_client import Error as SAMError, FileNotFound  # type: ignore

_LOCATION_SUFFIX_RE = re.compile(r'\([^)]+\)$')


class Mu2eName:
    """tier.owner.description.dsconf[.sequencer].extension -- fail loud."""

    def __init__(self, s: str):
        self.filename = s
        parts = s.split('.')
        if len(parts) == 6:
            (self.tier, self.owner, self.description, self.dsconf,
             self.sequencer, self.extension) = parts
        elif len(parts) == 5:
            self.tier, self.owner, self.description, self.dsconf, self.extension = parts
            self.sequencer = None
        else:
            raise ValueError(f"Invalid Mu2e name: expected 5 (dataset) or 6 (file/tarball) "
                             f"dot-separated fields, got {len(parts)} in '{s}'")

    @classmethod
    def parse(cls, s: str) -> "Mu2eName":
        return cls(s)

    @property
    def is_dataset(self) -> bool:
        return self.sequencer is None

    @property
    def dataset(self) -> "Mu2eName":
        if self.is_dataset:
            return self
        return Mu2eName('.'.join((self.tier, self.owner, self.description,
                                  self.dsconf, self.extension)))

    def __str__(self) -> str:
        return self.filename

    def __repr__(self) -> str:
        return f"Mu2eName({self.filename!r})"


class Mu2eJobPars:
    """The two members of a cnf jobdef tarball a generation reads."""

    def __init__(self, path: str):
        self.jobdef = path
        self._cache = {}
        self.json_data = json.loads(self._extract_member('jobpars.json'))

    def setup(self) -> str:
        """The Musing setup-script path recorded in jobpars.json."""
        return self.json_data.get('setup', '')

    def _extract_member(self, suffix: str) -> bytes:
        if suffix not in self._cache:
            with tarfile.open(self.jobdef, 'r') as tar:
                for member in tar.getmembers():
                    if member.name.endswith(suffix):
                        self._cache[suffix] = tar.extractfile(member).read()
                        break
                else:
                    raise ValueError(f"{suffix} not found in {self.jobdef}")
        return self._cache[suffix]


@lru_cache(maxsize=1)
def _client() -> SAMWebClient:
    experiment = os.environ.get('SAM_EXPERIMENT') or os.environ.get('EXPERIMENT') or 'mu2e'
    return SAMWebClient(experiment=experiment)


def count_files(query: str) -> int:
    return _client().countFiles(query)


def list_files(query: str) -> List[str]:
    return _client().listFiles(query)


def definitions_matching(defname: Optional[str] = None, user: Optional[str] = None) -> List[str]:
    kwargs = {}
    if defname:
        kwargs['defname'] = defname
    if user:
        kwargs['user'] = user
    result = _client().listDefinitions(**kwargs)
    if hasattr(result, '__iter__') and not isinstance(result, list):
        return list(result)
    return result


def locate_file(filename: str):
    """First location record (a dict), or "" when unknown / no locations."""
    try:
        locations = _client().locateFile(filename)
    except FileNotFound:
        return ""
    return locations[0] if locations else ""


def path_from_sam_location(filename: str, location) -> str:
    if not isinstance(location, dict):
        raise ValueError(f"malformed SAM location record for {filename}: {location!r}")
    path = location.get('full_path', '')
    for prefix in ('enstore:', 'dcache:'):
        if path.startswith(prefix):
            path = path[len(prefix):]
    path = _LOCATION_SUFFIX_RE.sub('', path)
    if not path:
        raise ValueError(f"empty path in SAM location record for {filename}")
    if not path.endswith(filename):
        path = f"{path.rstrip('/')}/{filename}"
    return path
