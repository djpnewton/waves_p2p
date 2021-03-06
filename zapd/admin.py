from flask import url_for
import flask_admin
from flask_admin import helpers as admin_helpers

from app_core import app, db
from models import security, RestrictedModelView, ProposalModelView, UserModelView, TransactionRestrictedModelView, AMWalletRestrictedModelView, \
    Role, User, Category, Proposal, Transaction, CreatedTransaction, AMWallet, AMDevice

# Create admin
admin = flask_admin.Admin(
    app,
    'ZAPD Admin',
    base_template='my_master.html',
    template_mode='bootstrap3',
)

# Add model views
admin.add_view(UserModelView(User, db.session, category='Admin'))
admin.add_view(RestrictedModelView(Role, db.session, category='Admin'))
admin.add_view(RestrictedModelView(Category, db.session, category='Admin'))
admin.add_view(AMWalletRestrictedModelView(AMWallet, db.session, name='App Metrics - Wallet', category='Admin'))
admin.add_view(ProposalModelView(Proposal, db.session))
admin.add_view(TransactionRestrictedModelView(Transaction, db.session, category='ZAPD'))
admin.add_view(RestrictedModelView(CreatedTransaction, db.session, category='ZAPD'))

# define a context processor for merging flask-admin's template context into the
# flask-security views.
@security.context_processor
def security_context_processor():
    return dict(
        admin_base_template=admin.base_template,
        admin_view=admin.index_view,
        h=admin_helpers,
        get_url=url_for
    )

