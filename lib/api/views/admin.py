from archii.api.schemas.company import CompanyQuestionnaireSchema
from archii.api.schemas.gdpr_names import GDPRPeopleSchema
from archii.api.schemas.user import UserSchema, AdminUserListSchema, \
    AccessUserSchema
from archii.api.views.base import BaseView


class View(BaseView):

    def get_all_users_view(self):
        all_users = self.controllers.get_all_users()
        return AdminUserListSchema(many=True).dump_data(
            all_users
        )

    def set_gdpr_names(self, gdpr_people):
        self.controllers.set_gdpr_names(gdpr_people)
        return GDPRPeopleSchema().dump_data(gdpr_people)

    def get_gdpr_names(self):
        c_employees, f_employees, c_customers, f_customers = \
            self.controllers.get_gdpr_names()
        return GDPRPeopleSchema().dump_data({
            "current_employees": [e.name for e in c_employees],
            "former_employees": [e.name for e in f_employees],
            "current_customers": [e.name for e in c_customers],
            "former_customers": [e.name for e in f_customers]
        })

    def disable_user_view(self, user_id):
        user = self.controllers.disable_user(user_id)
        return UserSchema().dump_data(user)

    def enable_user_view(self, user_id):
        user = self.controllers.enable_user(user_id)
        return UserSchema().dump_data(user)

    def send_invitations_view(self, schema):
        return AdminUserListSchema(many=True).dump_data(
            self.controllers.send_invitations(
                schema.user_emails,
                schema.message,
                schema.roles,
                schema.access_groups
            )
        )

    def create_company(self, schema):
        company = self.controllers.create_company(
            schema.company_names,
            schema.company_reg_number,
            schema.country_registration,
            schema.num_employees,
            schema.industry,
            schema.countries_operation
        )
        company_data = CompanyQuestionnaireSchema().dump_data(
            company.questionnaire_json
        )
        return company_data

    def get_company(self):
        return CompanyQuestionnaireSchema().dump_data(
            self.controllers.get_company()
        )

    def update_company(self, schema):
        company = self.controllers.update_company(schema.company_names,
                                                  schema.company_reg_number,
                                                  schema.country_registration,
                                                  schema.countries_operation,
                                                  schema.industry,
                                                  schema.num_employees)

        return CompanyQuestionnaireSchema().dump_data(
            company.questionnaire_json
        )

    def update_roles(self, access_dto, user_id):
        return AccessUserSchema().dump_data(
            self.controllers.update_roles(
                access_dto.access_groups,
                access_dto.roles,
                user_id
            )
        )
