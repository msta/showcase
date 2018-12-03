from .base import BaseController


class Controller(BaseController):
    def __init__(self, database=None):
        self.database = database

    def create_company(self,
                       company_names,
                       company_reg_number,
                       country_registration,
                       num_employees=None,
                       industry=None,
                       countries_operation=None
                       ) -> Company:
        user = self.get_current_user()
        return self.services.create_company(user.id,
                                            company_names,
                                            company_reg_number,
                                            country_registration,
                                            num_employees,
                                            industry,
                                            countries_operation)

    def set_gdpr_names(self, gdpr_people: GDPRPeopleSchema):
        user = self.get_current_user()
        current_employee = self.database.CurrentEmployee
        former_employee = self.database.FormerEmployee
        current_customer = self.database.CurrentCustomer
        former_customer = self.database.FormerCustomer
        company: Company = self.get_current_user().company
        company.gdpr_people.clear()
        for name in gdpr_people.current_employees:
            company.gdpr_people.add(current_employee(name=name))
        for name in gdpr_people.former_employees:
            company.gdpr_people.add(former_employee(name=name))
        for name in gdpr_people.current_customers:
            company.gdpr_people.add(current_customer(name=name))
        for name in gdpr_people.former_customers:
            company.gdpr_people.add(former_customer(name=name))

        # Rescan documents looking for the new names
        self.task_handler.revoke_and_send(
            "sensitive_documents",
            track_ids=[TrackID.GDPR_NAMES_UPDATE.format(company.id)],
            kwargs={
                "company_id": company.id,
                'user_id': user.id,
                'is_scan': False
            }
        )

    def get_gdpr_names(self):
        company: Company = self.get_current_user().company
        return [
            company.current_employees,
            company.former_employees,
            company.current_customers,
            company.former_customers
        ]

    def get_company(self):
        user = self.get_current_user()
        return user.company.questionnaire_json

    def update_company(self, company_names,
                       company_reg_number,
                       country_registration,
                       countries_operation,
                       industry,
                       num_employees):
        user = self.get_current_user()
        return self.services.update_company(user.id,
                                            company_names,
                                            company_reg_number,
                                            country_registration,
                                            countries_operation,
                                            industry,
                                            num_employees)

    def send_first_invitation(
        self,
        user_email,
        is_gdpr
    ):
        roles = {DefaultRole.Admin.value}
        if is_gdpr:
            roles.add(DefaultRole.GDPR.value)
        return self.services.create_and_invite_user(user_email, roles=roles)

    def send_invitations(
            self,
            user_emails,
            message,
            roles,
            access_groups
    ):
        inviter = self.get_current_user()
        existent_emails = []
        for email in user_emails:
            if self.database.email_exists(email):
                existent_emails.append(email)

        if existent_emails:
            raise APIError("Email already exists",
                           status_code=400, emails=existent_emails)

        invited_users = []
        for email in user_emails:
            user = self.services.create_and_invite_user(email,
                                                        inviter.company,
                                                        roles,
                                                        access_groups,
                                                        message,
                                                        inviter=inviter)
            invited_users.append(user)
        return invited_users

    def get_all_users(self):
        user = self.get_current_user()
        return user.company.users

    def disable_user(self, user_id):
        return self.database.disable_user(user_id)

    def enable_user(self, user_id):
        return self.database.enable_user(user_id)

    def update_roles(self, access_groups, roles, user_id):
        user = self.database.get_by_id(self.database.User,
                                       user_id)
        self.services.update_user_roles(user,
                                        access_groups,
                                        roles)
        return user
