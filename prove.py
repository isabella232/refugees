#!/usr/bin/env python

from collections import OrderedDict
import decimal
import json

import agate
import csvkit
import proof

FIRST_YEAR = 1990

SELECTED_COUNTRIES = [
    'Syrian Arab Rep.',
    'Colombia',
    'Iraq',
    'Dem. Rep. of the Congo',
    'Afghanistan',
    'Sudan',
    'South Sudan',
    'Somalia',
    'Pakistan',
    'Myanmar',
    'Libya',
    'Yemen',
    'Cote d\'Ivoire',
    'Ukraine',
    'Chad',
    'Eritrea',
    'Pakistan',
    'Bosnia and Herzegovina',
    'Rwanda',
    'Central African Rep.',
    'Nigeria'
]

MID_YEAR_2015 = {
    'Syrian Arab Rep.': 11925806,
    'Colombia': 6872447,
    'Iraq': 4485881,
    'Dem. Rep. of the Congo': 2415802,
    'Afghanistan': 3935141,
    'Sudan': 3078014,
    'South Sudan': 2540013,
    'Somalia': 2307686,
    'Pakistan': 2207555,
    'Myanmar': 891047,
    'Libya': 444412,
    'Yemen': 1279054,
    'Cote d\'Ivoire': 110669,
    'Ukraine': 1721545,
    'Chad': 86637,
    'Eritrea': 444091,
    'Bosnia and Herzegovina': 162869,
    'Rwanda': 94927,
    'Central African Rep.': 1004678,
    'Nigeria': 1668973,
    'total': 57959702
}

def load_data(data):
    """
    Load the dataset.
    """
    text_type = agate.Text()
    number_type = agate.Number()

    columns = OrderedDict([
        ('year', number_type),
        ('residence', text_type),
        ('origin', text_type),
        ('refugees', number_type),
        ('asylum_seekers', number_type),
        ('returned_refugees', number_type),
        ('idps', number_type),
        ('returned_idps', number_type),
        ('stateless_persons', number_type),
        ('others', number_type),
        ('total', number_type),
    ])

    # Load the data
    with open('unhcr_popstats_export_persons_of_concern_2016_01_12_192533.csv') as f:
        reader = csvkit.reader(f)
        next(reader)

        rows = []

        for row in reader:
            rows.append([None if d == '*' else d for d in row])

        data['table'] = agate.Table(rows, columns.keys(), columns.values())

def group(data):
    data['by_year'] = data['table']\
        .group_by('year')

    data['by_origin_2014'] = data['table']\
        .where(lambda r: r['year'] == 2014)\
        .group_by('origin')

def count_years(data):
    refugees = data['by_year'].aggregate([
        ('total_refugees', agate.Sum('refugees'), )
    ]).order_by('year')

    refugees.print_table()

    total = data['by_year'].aggregate([
        ('total_total', agate.Sum('total'), )
    ]).order_by('year')

    total.to_csv('years.csv')

def count_origins(data):
    refugees = data['by_origin_2014'].aggregate([
        ('total_refugees', agate.Sum('refugees'))
    ]).order_by('total_refugees', reverse=True)

    refugees.print_table(20)

def worst_country_year(data):
    country_year = data['table'].group_by(
        lambda r: ' / '.join([r['origin'], str(r['year'])]),
        key_name='origin_and_year'
    )

    refugees = country_year.aggregate([
        ('refugees', agate.Sum('refugees')),
        ('asylum_seekers', agate.Sum('asylum_seekers')),
        ('returned_refugees', agate.Sum('returned_refugees')),
        ('idps', agate.Sum('idps')),
        ('returned_idps', agate.Sum('returned_idps')),
        ('stateless_persons', agate.Sum('stateless_persons')),
        ('others', agate.Sum('others')),
        ('total', agate.Sum('total'))
    ]).order_by('total', reverse=True)

    refugees.print_table(30)

def subset(data):
    subset = data['table'].where(lambda r: r['origin'] in SELECTED_COUNTRIES and r['year'] >= 1980)
    groups = subset.group_by(
        lambda r: '/'.join([str(r['year']), r['origin']]),
        key_name='year_and_origin'
    )

    refugees = groups.aggregate([
        ('refugees', agate.Sum('refugees')),
        ('asylum_seekers', agate.Sum('asylum_seekers')),
        ('returned_refugees', agate.Sum('returned_refugees')),
        ('idps', agate.Sum('idps')),
        ('returned_idps', agate.Sum('returned_idps')),
        ('stateless_persons', agate.Sum('stateless_persons')),
        ('others', agate.Sum('others')),
        ('total', agate.Sum('total'))
    ]).order_by('year_and_origin', reverse=True)

    refugees = refugees.compute([
        ('year', agate.Formula(agate.Text(), lambda r: r['year_and_origin'].split('/')[0])),
        ('origin', agate.Formula(agate.Text(),  lambda r: r['year_and_origin'].split('/')[1]))
    ])

    refugees = refugees.select([
        'origin',
        'year',
        'refugees',
        'asylum_seekers',
        'idps',
        'returned_idps',
        'stateless_persons',
        'others',
        'total'
    ])

    refugees.to_csv('subset.csv')
    refugees.pivot('year', 'origin', agate.Sum('total')).order_by('year').to_csv('subset_pivot.csv')

def to_and_from(data):
    refugees = data['table'].select([
        'origin',
        'residence',
        'year',
        'refugees'
    ])

    by_year = refugees.group_by('year')

    by_origin = (by_year
        .group_by('origin')
        .aggregate([
            ('origin_refugees', agate.Sum('refugees'))
        ]))

    by_residence = (by_year
        .group_by('residence')
        .aggregate([
            ('residence_refugees', agate.Sum('refugees'))
        ]))

    def comparison(r):
        origin =  r['origin_refugees']
        residence = r['residence_refugees']

        if not origin:
            return None

        if not residence:
            return None

        return 1 - (abs(origin - residence) / (origin + residence))

    joined = (by_origin
        .join(by_residence, lambda r: (r['year'], r['origin']), lambda r: (r['year'], r['residence']))
        .exclude(['residence', 'year2'])
        .rename(column_names={ 'origin': 'country' })
        .compute([
            ('ratio', agate.Formula(agate.Number(), comparison))
        ]))

    joined.to_csv('joined.csv')

class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return float(o)
        return super(DecimalEncoder, self).default(o)

def graphic(data):
    data['grouped'] = (data['table']
        .group_by('origin')
        .group_by('year')
        .aggregate([
            ('total', agate.Sum('total'))
        ])
        .rename(row_names=lambda r: '%(origin)s-%(year)s' % r))

    countries = {}

    for country in SELECTED_COUNTRIES:
        years = []

        for year in range(FIRST_YEAR, 2015):
            try:
                name = '%s-%s' % (country, year)
                row = data['grouped'].rows[name]
                years.append(row['total'])
            except KeyError:
                years.append(None)

        years.append(MID_YEAR_2015[country])

        countries[country] = years

    totals = (data['table']
        .group_by('year')
        .aggregate([
            ('total', agate.Sum('total'))
        ])
        .rename(row_names=lambda r: str(r['year'])))

    years = []

    for year in range(FIRST_YEAR, 2015):
        row = totals.rows[str(year)]
        years.append(row['total'])

    years.append(MID_YEAR_2015['total'])

    countries['total'] = years

    with open('src/data/refugees.json', 'w') as f:
        json.dump(countries, f, cls=DecimalEncoder)

if __name__ == '__main__':
    data_loaded = proof.Analysis(load_data)
    grouped = data_loaded.then(group)
    grouped.then(count_years)
    grouped.then(count_origins)
    grouped.then(worst_country_year)
    grouped.then(subset)
    data_loaded.then(graphic)
    data_loaded.then(to_and_from)

    data_loaded.run()
