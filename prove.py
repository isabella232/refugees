#!/usr/bin/env python

import agate
import csvkit
import proof

def load_data(data):
    """
    Load the dataset.
    """
    text_type = agate.Text()
    number_type = agate.Number()
    boolean_type = agate.Boolean()

    columns = [
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
    ]

    # Load the data
    with open('unhcr_popstats_export_persons_of_concern_2015_09_02_224055.csv') as f:
        reader = csvkit.reader(f)
        reader.next()

        rows = []

        for row in reader:
            rows.append([None if d == '*' else d for d in row])

        data['table'] = agate.Table(rows, columns)

def group(data):
    data['by_year'] = data['table']\
        .group_by('year')

    data['by_origin_2014'] = data['table']\
        .where(lambda r: r['year'] == 2014)\
        .group_by('origin')

def count_years(data):
    refugees = data['by_year'].aggregate([
        ('refugees', agate.Sum(), 'total_refugees')
    ]).order_by('year')

    refugees.pretty_print()

def count_origins(data):
    refugees = data['by_origin_2014'].aggregate([
        ('refugees', agate.Sum(), 'total_refugees')
    ]).order_by('total_refugees', reverse=True)

    refugees.pretty_print(20)

def worst_country_year(data):
    country_year = data['table'].group_by(
        lambda r: ' / '.join([r['origin'], unicode(r['year'])]),
        key_name='origin_and_year'
    )

    refugees = country_year.aggregate([
        ('refugees', agate.Sum(), 'refugees'),
        ('asylum_seekers', agate.Sum(), 'asylum_seekers'),
        ('returned_refugees', agate.Sum(), 'returned_refugees'),
        ('idps', agate.Sum(), 'idps'),
        ('returned_idps', agate.Sum(), 'returned_idps'),
        ('stateless_persons', agate.Sum(), 'stateless_persons'),
        ('others', agate.Sum(), 'others'),
        ('total', agate.Sum(), 'total')
    ]).order_by('total', reverse=True)

    refugees.pretty_print(30)

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
        lambda r: '/'.join([unicode(r['year']), r['origin']]),
        key_name='year_and_origin'
    )

    refugees = groups.aggregate([
        ('refugees', agate.Sum(), 'refugees'),
        ('asylum_seekers', agate.Sum(), 'asylum_seekers'),
        ('returned_refugees', agate.Sum(), 'returned_refugees'),
        ('idps', agate.Sum(), 'idps'),
        ('returned_idps', agate.Sum(), 'returned_idps'),
        ('stateless_persons', agate.Sum(), 'stateless_persons'),
        ('others', agate.Sum(), 'others'),
        ('total', agate.Sum(), 'total')
    ]).order_by('year_and_origin', reverse=True)

    refugees.to_csv('subset.csv')

def graphic(data):
    counts = data['table'].select(['year', 'origin', 'refugees', 'total'])

    counts.to_csv('counts.csv')

if __name__ == '__main__':
    data_loaded = proof.Analysis(load_data)
    grouped = data_loaded.then(group)
    grouped.then(count_years)
    grouped.then(count_origins)
    grouped.then(worst_country_year)
    grouped.then(subset)
    data_loaded.then(graphic)

    data_loaded.run()
