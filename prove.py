#!/usr/bin/env python

from collections import OrderedDict
import decimal
import json

import agate
import csvkit
import proof

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
    countries = [
        'Syrian Arab Rep.',
        'Afghanistan',
        'Colombia',
        'Iraq',
        'Dem. Rep. of the Congo',
        'Rwanda',
        'Nepal',
        'Thailand',
        'Sudan',
        'Somalia'
    ]

    subset = data['table'].where(lambda r: r['origin'] in countries and r['year'] >= 1980)
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

class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return float(o)
        return super(DecimalEncoder, self).default(o)

def graphic(data):
    SELECTED_COUNTRIES = [
        'Ethiopia',
        'Afghanistan',
        'Iraq',
        'Bosnia and Herzegovina',
        'Nepal'
    ]

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

        for year in range(1975, 2015):
            try:
                name = '%s-%s' % (country, year)
                row = data['grouped'].rows[name]
                years.append(row['total'])
            except KeyError:
                years.append(None)

        countries[country] = years

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

    data_loaded.run()
