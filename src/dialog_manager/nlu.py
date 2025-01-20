from dataclasses import dataclass
from typing import Optional, Dict, List, Any


class NLUEntity:
    TYPE: Optional[str]

    def __init__(self, start_token, end_token, value):
        self.start_token: int = start_token
        self.end_token: int = end_token
        self.value: Any = value


class EntityDatetime(NLUEntity):
    TYPE = 'YANDEX.DATETIME'

    def __init__(self, start_token, end_token, value):
        super().__init__(start_token, end_token, value)

        self.year = value.get('year')
        self.month = value.get('month')
        self.day = value.get('day')
        self.hour = value.get('hour')
        self.minute = value.get('minute')

        self.relative = []
        for entry, res in value.items():
            if entry.endswith('_is_relative') and res:
                self.relative.append(entry.split('_')[0])


class EntityFIO(NLUEntity):
    TYPE = 'YANDEX.FIO'

    def __init__(self, start_token, end_token, value):
        super().__init__(start_token, end_token, value)

        self.first_name = value.get('first_name')
        self.patronymic_name = value.get('patronymic_name')
        self.last_name = value.get('last_name')


class EntityGEO(NLUEntity):
    TYPE = 'YANDEX.GEO'

    def __init__(self, start_token, end_token, value):
        super().__init__(start_token, end_token, value)

        self.country = value.get('country')
        self.city = value.get('city')
        self.street = value.get('street')
        self.house_number = value.get('house_number')
        self.airport = value.get('airport')


class EntityString(NLUEntity):
    TYPE = 'YANDEX.STRING'

    def __init__(self, start_token, end_token, value):
        super().__init__(start_token, end_token, value)


class EntityNumber(NLUEntity):
    TYPE = 'YANDEX.NUMBER'

    def __init__(self, start_token, end_token, value):
        super().__init__(start_token, end_token, value)


@dataclass
class Intent:
    """Распознанная в пользовательской реплике задача. Содержит слоты, которые хранят информацию
    об отдельных смысловых частях этой задачи."""

    name: str
    slots: Dict[str, NLUEntity]


@dataclass
class NLU:
    tokens: List[str]
    entities: List[NLUEntity]
    intents: Dict[str, Intent]


class NLUFactory:
    SUPPORTED_ENTITIES: List[NLUEntity] = [EntityNumber, EntityString, EntityGEO, EntityFIO, EntityDatetime]
    ENTITIES_MAP: Dict[str, type[NLUEntity]] = {e.TYPE: e for e in SUPPORTED_ENTITIES}

    @classmethod
    def construct(cls, nlu_json: Dict[str, Any]) -> NLU:
        tokens: List[str] = nlu_json['tokens']

        entities: List[NLUEntity] = []
        for entity_json in nlu_json['entities']:
            entity = cls.make_entity(entity_json)
            entities.append(entity)

        intents: Dict[str, Intent] = {}
        for intent_name, intent_json in nlu_json['intents'].items():
            slot_entities = {}
            for key, value in intent_json['slots'].items():
                slot_entities[key] = cls.make_entity(value)

            intents[intent_name] = Intent(intent_name, slot_entities)

        return NLU(tokens, entities, intents)

    @classmethod
    def make_entity(cls, entity_json: Dict[str, Any]) -> NLUEntity:
        entity_type: type[NLUEntity] = cls.ENTITIES_MAP.get(entity_json['type'])

        if entity_type is None:
            raise NameError(f'Entity {entity_json["type"]} not found; '
                            'Perhaps a custom entity is used and not registered.')

        start, end = entity_json['tokens'].values()
        value = entity_json['value']

        return entity_type(start, end, value)
