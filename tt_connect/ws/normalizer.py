from tt_connect.models import Tick
from tt_connect.instruments import Instrument


class TickNormalizer:
    def normalize(self, raw: dict, instrument: Instrument) -> Tick:
        raise NotImplementedError
