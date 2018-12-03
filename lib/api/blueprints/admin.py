from .base import BaseBlueprint
from ..auth import AuthenticationManager

auth = AuthenticationManager(database)

def admin_user_edit_permission(user_id):
    return [AdminPermission(), UserEditPermission(user_id)]


class Blueprint(BaseBlueprint):

    SCHEMAS = [('CompanyQuestionnaireSchema', CompanyQuestionnaireSchema),
               ('AdminUserListSchema', AdminUserListSchema),
               ('AccessUserSchema', AccessUserSchema),
               ('InviteUserSchema', InviteUserSchema),
               ('GDPRPeopleSchema', GDPRPeopleSchema)]

    def __init__(self, views=None, database=None):
        super().__init__('admin', views=views, database=database)

    def _set_routes(self):
        self.blueprint.route('/admin/users', methods=['GET'])(self.all_users)
        self.blueprint.route('/admin/user/<int:user_id>/access',
                             methods=['PUT'])(self.update_roles)
        self.blueprint.route('/admin/users/disable/<int:user_id>',
                             methods=['PUT'])(self.disable_user)
        self.blueprint.route('/admin/users/enable/<int:user_id>',
                             methods=['POST'])(self.enable_user)
        self.blueprint.route('/admin/users/invite',
                             methods=['POST'])(self.send_invitation)
        self.blueprint.route('/admin/company',
                             methods=['POST'])(self.create_company)
        self.blueprint.route('/admin/company')(self.get_company)
        self.blueprint.route('/admin/company',
                             methods=['PUT'])(self.update_company)
        self.blueprint.route(
            '/admin/gdpr-names', methods=['POST'])(self.set_gdpr_names)
        self.blueprint.route(
            '/admin/gdpr-names', methods=['GET'])(self.get_gdpr_names)

    def _configure(self):
        self.blueprint.add_app_url_map_converter(ListConverter, 'list')

    @auth.required
    def create_company(self):

        """
        Create a company. Can only create 1 company
        per admin user with no prior company linked.
        ---
        post:
            description: Create a company.
            consumes:
            - application/json
            parameters:
            - name: company
              in: body
              required: true
              schema: CompanyQuestionnaireSchema
            responses:
                200:
                    description: The created company
                    schema: CompanyQuestionnaireSchema
        """
        return self.views.create_company(
            CompanyQuestionnaireSchema().load_data()
        )

    @auth.required
    def set_gdpr_names(self):
        """
         Add names to search for when creating the sensitive
         document index.
        ---
        post:
            description: Add names.
            consumes:
            - application/json
            parameters:
            - name: gdpr_people
              in: body
              required: true
              schema: GDPRPeopleSchema
            responses:
                200:
                    description: The added names.
                    schema: GDPRPeopleSchema
        """
        authorize(AdminPermission())
        return self.views.set_gdpr_names(GDPRPeopleSchema().load_data())

    @auth.required
    def get_gdpr_names(self):
        """
         Add names to search for when creating the sensitive
         document index.
        ---
        get:
            description: Get current GDPR names.
            responses:
                200:
                    description: The added names.
                    schema: GDPRPeopleSchema
        """
        authorize(AdminPermission())
        return self.views.get_gdpr_names()

    @auth.required
    def get_company(self):
        """

        Get company and their associated questionnaire.
        ---
        get:
            description: Get company
            responses:
                200:
                    description: The company and it's questionnaire
                    schema: CompanyQuestionnaireSchema
        """
        return self.views.get_company()

    @auth.required
    def update_company(self):
        """

        Update company questionnaire
        ---
        put:
            description: Update an existing company.
            consumes:
            - application/json
            parameters:
            - name: company
              in: body
              required: true
              schema: CompanyQuestionnaireSchema
        """
        return self.views.update_company(
            CompanyQuestionnaireSchema().load_data()
        )

    @auth.required
    def all_users(self):
        """

        Get a list of all users and admin-related info
        ---
        get:
            description: Get a list of all users
            responses:
                200:
                    description: A list of users
                    schema:
                        type: array
                        items: AdminUserListSchema
        """
        return self.views.get_all_users_view()

    @auth.required
    def update_roles(self, user_id):
        """
        Update a users role and groups,
        ---
        put:
            description: Update a users groups and roles
            consumes:
            - application/json
            parameters:
            - name: groupsAndRoles
              in: body
              required: true
              schema: AccessUserSchema
            - name: userId
              in: path
              required: true
        :return:
        """

        authorize(admin_user_edit_permission(user_id))
        return self.views.update_roles(
            AccessUserSchema().load_data(),
            user_id
        )

    # Disable user
    @auth.required
    def disable_user(self, user_id):

        authorize(admin_user_edit_permission(user_id))
        return self.views.disable_user_view(user_id)

    # Enable user
    @auth.required
    def enable_user(self, user_id):

        authorize(admin_user_edit_permission(user_id))
        return self.views.enable_user_view(user_id)

    # Send invitation
    @auth.required
    def send_invitation(self):
        """

        Invite new users to the company
        ---
        post:
            description: Invite new users to the company.
            consumes:
            - application/json
            parameters:
            - name: invite
              in: body
              required: true
              schema: InviteUserSchema
            responses:
                200:
                    description: A list of invited users
                    schema:
                        type: array
                        items: AdminUserListSchema
        """
        authorize(AdminPermission())
        return self.views.send_invitations_view(
            InviteUserSchema().load_data()
        )
