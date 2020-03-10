from .token import Token

class UDToken(Token):
    pass

from . import ud_properties
from . import ud_tagset

ud_properties.set_tagset(UDToken)
ud_tagset.set_tagset(UDToken)

