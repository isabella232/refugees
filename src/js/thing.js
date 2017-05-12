var fm = require('./fm');
var throttle = require('./throttle');
var features = require('./detectFeatures')();
var d3 = require('d3');
var request = require('d3-request');
var _ = require('lodash');

var FIRST_YEAR = 1990;
var LAST_YEAR = 2015;
var MOBILE_THRESHOLD = 600;

// D3 formatters
var fmtComma = d3.format(',');
var fmtYearAbbrev = d3.time.format('%y');
var fmtYearFull = d3.time.format('%Y');

var refugeeData = {};
var isMobile = false;

function init () {
	request.requestJson('./data/refugees.json', function(err, data) {
		refugeeData = data;

		update();
	});
}

function update () {
	var width = $('#interactive-content').width();

	if (width <= MOBILE_THRESHOLD) {
		isMobile = true;
	} else {
		isMobile = false;
	}

	_.each(refugeeData, function(data, country) {
		if (country == 'total') {
			return;
		}

		var id = '#' + classify(country);

		// Render the chart!
		renderColumnChart({
			container: id,
			width: $(id).width(),
			data: data,
			aspectRatio: 2,
			max: 12,
			yTicks: isMobile ? [0, 6, 12] : [0, 3, 6, 9, 12]
		});

        createDownloadLink(id);
	});

	// Render the chart!
	renderColumnChart({
		container: '#total',
		width: width,
		data: refugeeData['total'],
		aspectRatio: 1,
		max: 60,
		yTicks: [0, 15, 30, 45, 60]
	});

    createDownloadLink('#total');

	// adjust iframe for dynamic content
	fm.resize()
}

function resize() {
	update()
}

var createDownloadLink = function(slug) {
    //get svg element.
    var svg = d3.select(slug + ' svg')[0][0];

    if(_.isUndefined(svg) || _.isNull(svg)) {
        return;
    }

    //get svg source.
    var serializer = new XMLSerializer();
    var source = serializer.serializeToString(svg);

    //add name spaces.
    if(!source.match(/^<svg[^>]+xmlns="http\:\/\/www\.w3\.org\/2000\/svg"/)){
        source = source.replace(/^<svg/, '<svg xmlns="http://www.w3.org/2000/svg"');
    }

    if(!source.match(/^<svg[^>]+"http\:\/\/www\.w3\.org\/1999\/xlink"/)){
        source = source.replace(/^<svg/, '<svg xmlns:xlink="http://www.w3.org/1999/xlink"');
    }

    //add xml declaration
    source = '<?xml version="1.0" standalone="no"?>\r\n' + source;

    //convert svg source to URI data scheme.
    var url = "data:image/svg+xml;charset=utf-8,"+encodeURIComponent(source);

    console.log(slug);
    console.log(d3.select('#download-' + slug));

    //set url value to a element's href attribute.
    var anchor = d3.select('#download-' + slug.substring(1));
    anchor.attr('href', url);
    anchor.attr('download', slug.substring(1) + '.svg');
}

/*
 * Render a column chart.
 */
var renderColumnChart = function(config) {
	/*
	 * Setup chart container.
	 */
	var margins = {
		top: 10,
		right: 5,
		bottom: 25,
		left: 30
	};

	// Calculate actual chart dimensions
	var chartWidth = config['width'] - margins['left'] - margins['right'];
	var chartHeight = Math.ceil(config['width'] / config['aspectRatio']) - margins['top'] - margins['bottom'];

	// Clear existing graphic (for redraw)
	var containerElement = d3.select(config['container']);
	containerElement.html('');

	/*
	 * Create the root SVG element.
	 */
	var chartWrapper = containerElement.append('div')
		.attr('class', 'graphic-wrapper');

	var chartElement = chartWrapper.append('svg')
		.attr('width', chartWidth + margins['left'] + margins['right'])
		.attr('height', chartHeight + margins['top'] + margins['bottom'])
		.append('g')
		.attr('transform', 'translate(' + margins['left'] + ',' + margins['top'] + ')');

	/*
	 * Create D3 scale objects.
	 */
	var domain = [];

	for (i = FIRST_YEAR; i <= LAST_YEAR; i++) {
		domain.push(i);
	}

	var xScale = d3.scale.ordinal()
		.rangeRoundBands([0, chartWidth], .1)
		.domain(domain);

	var yScale = d3.scale.linear()
		.range([chartHeight, 0])
		.domain([0, config['max']]);

	/*
	 * Create D3 axes.
	 */
	var xAxis = d3.svg.axis()
	.scale(xScale)
	.orient('bottom')
	.tickFormat(function(d, i) {
		if (i % 5 != 0) {
			return '';
		}

		if (isMobile) {
			return "'" + d.toString().substring(2, 4);
		}

		return d;
	});

	var yAxis = d3.svg.axis()
		.scale(yScale)
		.orient('left')
		.tickValues(config['yTicks'])
		.tickFormat(function(d, i) {
			var label = fmtComma(d);

			return label;
		});

	/*
	 * Render axes to chart.
	 */
	var xAxisElement = chartElement.append('g')
		.attr('class', 'x axis')
		.attr('transform', makeTranslate(0, chartHeight))
		.call(xAxis);

	var yAxisElement = chartElement.append('g')
		.attr('class', 'y axis')
		.call(yAxis)

	/*
	 * Render grid to chart.
	 */
	var yAxisGrid = function() {
		return yAxis;
	};

	yAxisElement.append('g')
		.attr('class', 'y grid')
		.call(yAxisGrid()
			.tickSize(-chartWidth, 0)
			.tickFormat('')
		);

	/*
	 * Render bars to chart.
	 */
	chartElement.append('g')
		.attr('class', 'bars')
		.selectAll('rect')
		.data(config['data'])
		.enter()
		.append('rect')
			.attr('x', function(d, i) {
				return xScale(FIRST_YEAR + i);
			})
			.attr('y', function(d) {
				return yScale(d / 1000000);
			})
			.attr('width', xScale.rangeBand())
			.attr('height', function(d) {
				return yScale(0) - yScale(d / 1000000);
			})
			.attr('class', function(d) {
				return 'bar';
			});
}

/*
 * Convert arbitrary strings to valid css classes.
 * via: https://gist.github.com/mathewbyrne/1280286
 */
var classify = function(str) {
	return str.toLowerCase()
		.replace(/\s+/g, '-')					 // Replace spaces with -
		.replace(/[^\w\-]+/g, '')			 // Remove all non-word chars
		.replace(/\-\-+/g, '-')				 // Replace multiple - with single -
		.replace(/^-+/, '')						 // Trim - from start of text
		.replace(/-+$/, '');						// Trim - from end of text
}

/*
 * Convert key/value pairs to a style string.
 */
var formatStyle = function(props) {
	var s = '';

	for (var key in props) {
		s += key + ': ' + props[key].toString() + '; ';
	}

	return s;
}

/*
 * Create a SVG tansform for a given translation.
 */
var makeTranslate = function(x, y) {
	var transform = d3.transform();

	transform.translate[0] = x;
	transform.translate[1] = y;

	return transform.toString();
}

var throttleRender = throttle(resize, 250);

$(document).ready(function () {
	// adjust iframe for loaded content
	fm.resize()
	$(window).resize(throttleRender);
	init();
});
