from typing import Optional

class IntegrationFactory(object):
    @staticmethod
    def get_integration(integration_name: str,
                        credentials: dict,
                        scan_id: Optional[int],
                        process_callback=None,
                        download_path=None) -> IntegrationProcess:
        strategy_instance = IntegrationFactory.get_integration_strategy(
            integration_name,
            credentials
        )

        process = IntegrationProcess(strategy_instance,
                                     credentials,
                                     scan_id,
                                     process_callback=process_callback,
                                     download_path=download_path)
        return process

    @staticmethod
    def get_integration_strategy(integration_name, credentials):
        if integration_name not in list(INTEGRATIONS):
            Log().error("Unknown integration", integration=integration_name)
            raise ValueError(
                'Unknown integration: {}'.format(
                    integration_name
                )
            )
        strategy_cls = integrations_clz_map[integration_name]  # noqa: N806
        strategy_instance = strategy_cls(credentials)
        return strategy_instance
