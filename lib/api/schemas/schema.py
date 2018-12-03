from marshmallow import Schema, pre_dump, post_load
import toastedmarshmallow

class SomeCompanySchema(Schema):
    class Meta:
        jit = toastedmarshmallow.Jit

    _default_json_loader = None
    _json_serializer = None

    @classmethod
    def set_default_json_loader(cls, loader):
        """
        Sets a default loader for getting data to de-serialize
        in the schema. If the loader is unset the data must be passed
        to load_data explicitly.
        :param loader:
        :return:
        """
        cls._default_json_loader = loader

    def __init__(self, *args, strict=True, **kwargs):
        super().__init__(*args,
                         strict=strict,
                         **kwargs)

    @post_load
    def make_dto(self, data):
        dto_keys = self.declared_fields
        dto_dict = {k: None for (k, v) in dto_keys.items()}
        dto_instance = create_dto_class(dto_dict)
        for key in data.keys():
            setattr(dto_instance, key, data[key])
        return dto_instance

    def load_data(self,
                  json_data=None,
                  many=None,
                  *args,
                  **kwargs):
        if not json_data:
            if not SomeCompanySchema._default_json_loader:
                raise ValueError("No json data could be loaded. Set a loader"
                                 " or pass it with the json_data param")
            json_data = SomeCompanySchema._default_json_loader()

        json_data = check_case_recursive(json_data)

        return self.load(
            json_data,
            many=many,
            *args,
            **kwargs
        ).data

    def dump_data(self,
                  obj,
                  many=None,
                  update_fields=True,
                  enable_json_serializer=True,
                  **kwargs):
        data = self.dump(obj,
                         many=many,
                         update_fields=update_fields,
                         **kwargs).data
        data = check_case_recursive(data, dump=True)
        if enable_json_serializer:
            if not SomeCompanySchema._json_serializer:
                raise ValueError('The json serializer is not set. '
                                 'Use set_json_serializer')

            data = SomeCompanySchema._json_serializer(
                data
            )
        return data

    @classmethod
    def set_json_serializer(cls, serializer):
        cls._json_serializer = serializer


class PonyAdapterSchema(SomeCompanySchema):
    def __init__(self, *args, strict=True, **kwargs):
        super().__init__(*args,
                         strict=strict,
                         **kwargs)

    @pre_dump
    def to_dto_and_convert(self, pony_object):
        if not pony_object.__class__.__name__ == DTO_NAME:
            dto = database.models.to_DTO(
                pony_object
            )
        else:
            dto = pony_object
        return self.convert(dto, pony_object)

    def convert(self, dto, original):
        return dto
