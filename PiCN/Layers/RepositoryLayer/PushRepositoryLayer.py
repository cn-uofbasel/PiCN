"""Push Repository Layer"""

import multiprocessing
import base64

from PiCN.Layers.ICNLayer.ContentStore import BaseContentStore
from PiCN.Packets import Packet, Interest, Nack, NackReason, Content
from PiCN.Processes import LayerProcess

from PiCN.Layers.NFNLayer.Parser import DefaultNFNParser
from PiCN.Layers.NFNLayer.Parser.AST import *


def is_publish_expression(ast) -> bool:
    if ast.type == AST_FuncCall:
        return ast._element == "/remote/publish" and len(ast.params) == 2 and isinstance(ast.params[0], AST_Name) \
               and isinstance(ast.params[1], AST_String)
    return False


class PushRepositoryLayer(LayerProcess):
    """Push Repository Layer"""

    def __init__(self, cs: BaseContentStore = None, log_level=255):
        super().__init__(logger_name="PushRepoLyr", log_level=log_level)
        self.cs = cs

    def data_from_higher(self, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, data):
        pass  # this is already the highest layer

    def data_from_lower(self, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, data):
        if len(data) != 2:
            self.logger.warning("PushRepo Layer expects to receive [face_id, Interest] from lower layer")
            return
        if type(data[0]) != int:
            self.logger.warning("PushRepo Layer expects to receive [face_id, Interest] from lower layer")
            return
        if not isinstance(data[1], Packet):
            self.logger.warning("PushRepo Layer expects to receive [face_id, Interest] from lower layer. Drop.")
            return
        face_id = data[0]
        interest = data[1]
        self.handle_interest_from_lower(face_id, interest, to_lower)

    def handle_interest_from_lower(self, face_id: int, interest: Interest, to_lower: multiprocessing.Queue):
        self.logger.info("Incoming interest: " + interest.name.to_string())
        # incoming interest is nfn expression
        if interest.name.string_components[-1] == "NFN":
            try:
                parser = DefaultNFNParser()
                nfn_str, prepended_name = parser.network_name_to_nfn_str(interest.name)
                ast = parser.parse(nfn_str)
                # assert that valid publish expression
                if is_publish_expression(ast):
                    # store to database
                    data_name = ast.params[0]._element
                    payload = ast.params[1]._element
                    try:
                        payload = base64.b64decode(payload[7:])
                        self.logger.info("Payload is base64 encoded. Decoded.")
                    except:
                        self.logger.info("Invalid publish expression. The payload could not be decoded.")
                        nack = Nack(interest.name, reason=NackReason.COMP_NOT_PARSED, interest=interest)
                        self.queue_to_lower.put([face_id, nack])

                    self.cs.add_content_object(Content(data_name, payload))
                    self.logger.info("Add to database: " + data_name)
                    # reply confirmation
                    confirmation = Content(interest.name, "ok")
                    to_lower.put([face_id, confirmation])

                else:
                    self.logger.info("Invalid publish expression. Wrong format.")
                    nack = Nack(interest.name, reason=NackReason.COMP_NOT_PARSED, interest=interest)
                    self.queue_to_lower.put([face_id, nack])

            except:
                self.logger.info("Invalid publish expression.")
                nack = Nack(interest.name, reason=NackReason.COMP_NOT_PARSED, interest=interest)
                self.queue_to_lower.put([face_id, nack])

        # incoming interest is data request
        else:
            db_entry = self.cs.find_content_object(interest.name)
            if db_entry is not None:
                self.logger.info("Found in database")
                to_lower.put([face_id, db_entry.content])
                return
            else:
                self.logger.info("Not found in database")
                nack = Nack(interest.name, NackReason.NO_CONTENT, interest)
                to_lower.put([face_id, nack])
                return
