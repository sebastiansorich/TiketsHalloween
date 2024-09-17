from flask import Blueprint
from ..controllers.ticket_controller import create_ticket, get_tickets, verify_ticket, use_ticket,delete_ticket, delete_ticket_by_token, generate_qr,generate_invitation_with_qr

ticket_bp = Blueprint('tickets', __name__)

ticket_bp.route('/tickets', methods=['POST'])(create_ticket)
ticket_bp.route('/tickets', methods=['GET'])(get_tickets)
ticket_bp.route('/tickets/verify/<string:token>', methods=['POST'])(verify_ticket)
ticket_bp.route('/tickets/use/<string:token>', methods=['POST'])(use_ticket)
ticket_bp.route('/tickets/delete/<string:token>', methods=['DELETE'])(delete_ticket_by_token)
ticket_bp.route('/tickets/delete/<int:id>', methods=['DELETE'])(delete_ticket)
ticket_bp.route('/tickets/<string:token>/qr', methods=['GET'])(generate_qr)
ticket_bp.route('/tickets/<string:token>/invitation', methods=['GET'])(generate_invitation_with_qr)




