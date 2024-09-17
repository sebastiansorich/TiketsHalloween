from .. import ma
from ..models.ticket import Ticket

class TicketSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Ticket
        load_instance = True

ticket_schema = TicketSchema()
tickets_schema = TicketSchema(many=True)
