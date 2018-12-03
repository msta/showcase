import re as regex
from typing import NamedTuple, List, Sequence, Any


def _clean_name(name):
    """
    Remove initials (i.e single letters surrounded by whitespace followed by an
    optional period) as well as lone periods.
    :param name: name to clean
    :return: name without initials and periods
    """
    pattern = r'(\b[A-Za-z]\.? ?\b)|\.'
    return regex.sub(pattern, '', name).strip()


def _make_name_queries(people: List[GDPRPerson], exact: bool):
    def count_middle_names(name):
        ns = name.split()
        names_len = len(ns)
        if names_len > 1:
            # if there is more than one name,
            # assume that 1 is first and 1 is last
            # and rest is middle names
            return names_len - 2
        return 0

    def remove_middle_names(name):
        ns = name.split()
        names_count = len(ns)
        if names_count > 1:
            first, *middle, last = ns
            return f'{first} {last}'
        return name

    def partial_match_query(n):
        # return MultiMatch(query=n, fields=['text', 'name'])
        return Match(text=n) | Match(name=n)

    def exact_match_query(n):
        max_middle_names = config.get().search_config.max_middle_names
        middle_names = count_middle_names(n)
        if middle_names <= max_middle_names:
            # if number of middle names is low enough
            # to trigger special case
            # search for name without middle names
            name = remove_middle_names(n)
            # but allow exact matches to include
            # up to max_middle_names of extra names
            # see:
            # https://github.com/archiidev/background/wiki/Semantics-of-GDPR-Search
            slop = max_middle_names
        else:
            slop = 0
            name = n
        query = {'query': name, 'slop': slop}
        return MatchPhrase(text=query) | MatchPhrase(name=query)

    if exact:
        names = [person.name for person in people]
    else:
        names = [_clean_name(person.name) for person in people]
        names = [name for name in names if name != '']
    query_type = exact_match_query if exact else partial_match_query
    return [query_type(name) for name in names]


def _high_risk_keywords_query(high_risk_keywords):
    queries = [MatchPhrase(text={'_name': keyword, 'query': keyword})
               for keyword in set(high_risk_keywords)]
    return Q('bool',
             should=queries)


def _get_match_range(person: 'GDPRPerson', hit) -> tuple:
    """
    Given a name and a hit, determines the range in name for which a match
    was found in either hit's text or name property.
    """
    cleaned = _clean_name(person.name)
    name_parts = regex.compile(r"[ \-]").split(cleaned)
    with_word_boundaries = [r"\b({})\b".format(name)
                            for name in name_parts]
    name_pattern = '|'.join(with_word_boundaries)
    match = regex.search(name_pattern, hit.text, regex.IGNORECASE)
    if match is None:
        match = regex.search(name_pattern, hit.name, regex.IGNORECASE)
    # get first matched group
    matched_name_part = next(g for g in match.groups() if g is not None)
    start_index = person.name.lower().find(matched_name_part.lower())
    end_index = start_index + len(matched_name_part)
    return start_index, end_index


def _language_query(language):
    return MatchPhrase(language=language.code)


def _make_included_ids_query(company):
    return Ids(values=company.included_document_ids)


@curry
@time
def _high_risk_query(people: List[GDPRPerson],
                     company: Company,
                     exact: bool) -> Sequence[Any]:
    client = config.get().search_config.client
    name_queries = _make_name_queries(people, exact)
    included_ids_query = _make_included_ids_query(company)
    with database.session:
        languages = get_languages()

    results = []
    for language in languages:
        high_risk_keywords = (config
                              .get()
                              .search_config.high_risk_keywords[language.code])
        keyword_query = _high_risk_keywords_query(high_risk_keywords)
        language_query = _language_query(language)
        for person, name_query in zip(people, name_queries):
            search = Search().using(client).index(str(company.id)).query()

            search = search.filter(
                included_ids_query
            ).filter(
                language_query
            ).filter(
                keyword_query
            ).filter(
                name_query
            )
            response = search.scan()
            for hit in response:
                for keyword in hit.meta.matched_queries:
                    if exact:
                        result = HighRiskSearchResult(
                            doc_id=hit.meta.id,
                            gdpr_name=person.name,
                            keyword=keyword,
                            relation=person.relation
                        )
                        results.append(result)
                    else:
                        try:
                            result = HighRiskPartialSearchResult(
                                doc_id=hit.meta.id,
                                gdpr_name=person.name,
                                keyword=keyword,
                                match_range=_get_match_range(person, hit),
                                relation=person.relation
                            )
                            results.append(result)
                        except Exception:
                            Log().exception(
                                'Error while creating search result',
                                document_id=hit.meta.id,
                                name=person.name,
                                keyword=keyword
                            )
    return results

