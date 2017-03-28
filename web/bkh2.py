import feather
from bokeh.document import Document
from bokeh.plotting import figure, output_file, show,ColumnDataSource
from bokeh.models.formatters import DatetimeTickFormatter
from bokeh.models.ranges import Range1d
from bokeh.models import (Plot,FixedTicker,HoverTool,DatetimeAxis,
                          Grid,LinearAxis,Label,BasicTicker,DataRange1d,Span)
from bokeh.models.glyphs import Line,Ellipse,Text,HBar,MultiLine,Circle
from bokeh.models.tools import HoverTool,SaveTool, ResetTool
from bokeh.layouts import column,gridplot
from bokeh.embed import components
from bokeh.resources import INLINE
import bokeh.palettes as bp
from bokeh.util.string import encode_utf8
import numpy as np
import time
import flask
from datetime import datetime,timedelta
import jinja2

def render_without_request(template_name, **template_vars):
    env = jinja2.Environment( loader=jinja2.FileSystemLoader("./")    )
    template = env.get_template(template_name)
    return template.render(**template_vars)

js_resources = INLINE.render_js()
css_resources = INLINE.render_css()


epoch = datetime.utcfromtimestamp(0)
def unix_time_millis(dt):
    return (dt - epoch).total_seconds() * 1000.0

v=feather.read_dataframe("./alldiall.feather")
v2016 = v.loc[v['year']=='2016']
v2017 = v.loc[v['year']=='2017']

def ExpandedRange(vector,expand_factor=0.1):
    ymax = np.nanmax(list(set().union(*vector)))
    ymin = np.nanmin(list(set().union(*vector)))
    ymax = ymax+(ymax-ymin)*expand_factor/2
    ymin = ymin-(ymax-ymin)*expand_factor/2
    return (ymin,ymax)


ymin,ymax = ExpandedRange([v['sDauAc'],v['sDauSub'],v['sAdi']], 0.1)

def YoY(dd,yaxislabel,isbottompanel,istoppanel,legend_location):
    line_colors = bp.Category10[3]
    basedate = datetime.strptime("20170101", "%Y%m%d")
    newaxis = [basedate+timedelta(x) for x in dd['doy']]
    source = ColumnDataSource(
        data=dict(
            x = newaxis,
#            xd = [ x.strftime( "%s-%m-%d" % yaxislabel) for x in newaxis],
            xd2 = dd['date'],
            sDauAc=dd['sDauAc'],
            sDauSub = dd['sDauSub'],
            sAdi = dd['sAdi']
        )
    )
    p = figure(plot_width=1000,
               plot_height=250,
               y_range = [ymin,ymax],
               x_range = Range1d( datetime.strptime("20161228", "%Y%m%d"),
                                  datetime.strptime("20180105", "%Y%m%d"))
               )
               # ,tools=[hover])
    ## Not toolbars (but they come back when used in  a grid plot)
    p.toolbar.logo = None
    p.toolbar_location = None
    ## axis labels
    p.yaxis.axis_label = yaxislabel
    ## Format the bottom x-axis (only if bottom)
    p.xaxis.formatter = DatetimeTickFormatter(days="%d/%b",months="%b")
    if isbottompanel:
        p.xaxis[0].ticker = FixedTicker(ticks=[unix_time_millis(datetime.strptime(x, "%Y%m%d")) for x in
                                               ("20170101","20170201",'20170301','20170401','20170501','20170601',
                                                '20170701',"20170801","20170901",'20171001','20171101','20171201','20180101')])
    else:
        p.xaxis[0].ticker = FixedTicker(ticks=[unix_time_millis(datetime.strptime(x, "%Y%m%d")) for x in  ("20010101","22000101")])
    ## We want a black border for aesthetic reasons, make a blank axis
    rightaxis = LinearAxis(axis_label=None)
    rightaxis.ticker= FixedTicker()
    p.add_layout(rightaxis, 'right')
    ## And a top axis, but is blank if this is not the top plot
    topxaxis = DatetimeAxis(axis_label=None)
    if not istoppanel:
        topxaxis.ticker = FixedTicker()
    else:
        topxaxis.formatter = DatetimeTickFormatter(days="%d/%b",months="%b")
        topxaxis.ticker = FixedTicker(ticks=[unix_time_millis(datetime.strptime(x, "%Y%m%d")) for x in
                                             ("20170101","20170201",'20170301','20170401','20170501','20170601','20170701'
                                              ,"20170801","20170901",'20171001','20171101','20171201','20180101')])
    p.add_layout(topxaxis, 'above')
    ## Add the three series
    r1 = p.line('x', 'sDauAc', source=source,legend = "ActivityDate", color=line_colors[0], line_width=2)
    r2 = p.line('x', 'sAdi', source=source,legend = "Blocklist", color=line_colors[2], line_width=2)
    r3 = p.line('x', 'sDauSub',source=source, legend = "SubmissionDate", color=line_colors[1], line_width=2)
    p.add_tools(HoverTool(tooltips =[
        ("date","@xd2"),
        ("activityDate","@sDauAc"),
        ("blocklist","@sAdi"),
        ("submissionDate","@sDauSub")
    ],renderers = [r2], mode='vline'))
                
    ## Adjust Grids - we don't want vertical grids
    p.xgrid.grid_line_color = None
    p.ygrid.bounds = ( ymin + (ymax-ymin)*0.15,ymax - (ymax-ymin)*0.15)
    ## Specify Legend Location (it's alternating)
    p.legend.location=legend_location
    p.legend.background_fill_alpha = 0
    return p


pbottom = YoY(v2016,yaxislabel='2016',istoppanel=False,isbottompanel=True,legend_location='top_left')
ptop = YoY(v2017,yaxislabel='2017',istoppanel=True,isbottompanel=False,legend_location='top_right')



yoy=gridplot([ptop,pbottom],ncols=1,merge_tools = True, toolbar_options={'logo': None})

w=feather.read_dataframe("./ladi.feather")
line_colors = bp.Category10[4]
w = w.assign(color = map(lambda yr: line_colors[int(yr)-2014], list(w['year'])))

def YoYADI(w,varname,LAB):
    yrange = ExpandedRange([w[varname]], 0.1)
    xrange = [-5,370]
    colp = []
    basedate = datetime.strptime("20170101", "%Y%m%d")
    for year in ('2017','2016','2015','2014'):
        s  = w.loc[w['year']==year]
        s=s.sort(['doy'])
        newaxis = [basedate+timedelta(x) for x in s['doy']]
        source = ColumnDataSource(
            data=dict(
                date = s['date'],
                x = newaxis,
                adi  = s[varname]
            )
        )
        p = figure(plot_width=1000,
                   plot_height=150,
                   y_range = yrange,
                   x_range = Range1d( datetime.strptime("20161228", "%Y%m%d"),
                                      datetime.strptime("20180105", "%Y%m%d"))
        )
        p.xaxis.formatter = DatetimeTickFormatter(days="%d/%b",months="%b")
        if year=='2014':
            p.xaxis[0].ticker = FixedTicker(ticks=[unix_time_millis(datetime.strptime(x, "%Y%m%d")) for x in
                                                   ("20170101","20170201",'20170301','20170401','20170501','20170601',
                                                    '20170701',"20170801","20170901",'20171001','20171101','20171201','20180101')])
        else:
            p.xaxis[0].ticker = FixedTicker(ticks=[unix_time_millis(datetime.strptime(x, "%Y%m%d")) for x in  ("20010101","22000101")])

        topxaxis = DatetimeAxis(axis_label=None)
        if year!='2017':
            topxaxis.ticker = FixedTicker()
        else:
            topxaxis.formatter = DatetimeTickFormatter(days="%d/%b",months="%b")
            topxaxis.ticker = FixedTicker(ticks=[unix_time_millis(datetime.strptime(x, "%Y%m%d")) for x in
                                             ("20170101","20170201",'20170301','20170401','20170501','20170601','20170701'
                                              ,"20170801","20170901",'20171001','20171101','20171201','20180101')])
        p.add_layout(topxaxis, 'above')
        rightaxis = LinearAxis(axis_label=None)
        rightaxis.ticker= BasicTicker()
        p.add_layout(rightaxis, 'right')
        p.toolbar.logo = None
        p.yaxis[0].axis_label = year
        o=p.line(x="x",y="adi",source=source,line_width=2)
        p.ygrid.band_fill_alpha = 0.1
        p.ygrid.band_fill_color = "grey"
        p.add_tools(HoverTool(tooltips =[
            ("date","@date"),
            (LAB,"@adi")
    ],renderers = [o], mode='vline'))

        colp.append(p)
    return gridplot(colp,ncols=1,merge_tools = True, toolbar_options={'logo': None})
    
        

def Cycle(varname,tooltips=None,functor=None):
    ymin,ymax = ExpandedRange([w[varname]], 0.1)
    xmin,xmax = ExpandedRange(  [ [1.0], list( w['id'])], 0.05)
    xdr = DataRange1d(bounds=None)
    ydr = DataRange1d(bounds=None)
    allPlots = []
    LM = ('Jan','Apr','Jul','Oct')
    RM = ('Mar','Jun','Sep','Dec')
    for mo in ('Oct','Nov',"Dec","Jul",'Aug','Sep','Apr','May','Jun','Jan',"Feb","Mar"):
        def addAxis(p,side):
            xaxis = LinearAxis()
            xaxis.ticker =FixedTicker()
            p.add_layout(xaxis, side)
        x1 = w.loc[w['month'] == mo]
        mbl = 0
        mbb = 0
        plot = Plot(
            y_range = Range1d(ymin,ymax),
            x_range = Range1d(xmin,xmax),
            plot_width=330 + mbl, plot_height=200 + mbb,
            min_border_left=2+mbl, min_border_right=2,
            min_border_top=1, min_border_bottom=0+mbb,tools=[SaveTool(),ResetTool()])
        plot.title.text=mo
        ly = None
        mymeans = []
        myxmeans = []
        rr = []
        for i,yr in enumerate(('2014','2015','2016','2017')):
            data = x1.loc[x1['year']==yr]
            source = ColumnDataSource(data=dict(date=data['date'],
                                                i = data['id'],
                                                adi = data[varname],
                                                TYvsLY = ["%0.2f%%" % x for x in data['reldiff']],
                                                delta = data['diff']          
            ))
            mymeans.append( float(np.nanmean( data[varname]) ))
            myxmeans.append(float( np.nanmean(data['id'])))
            l= Line(x='i', y='adi',line_color=line_colors[i],line_width=2)
            r = plot.add_glyph(source, l)
            rr.append(r)
            #xdr.renderers.append(r)
            #ydr.renderers.append(r)

        #print([ varname,mo,mymeans])
        tylareldiff =  [ np.nan,]
        [ tylareldiff.append(x) for x in  [ "%.2f" % (100*(fu-pa)/pa) for fu,pa in zip(mymeans[1:],  mymeans[:-1])]]
        meancds = ColumnDataSource(data=dict(x = myxmeans, year = mymeans,reldiff=tylareldiff,color=line_colors))
        mc = Circle( x= "x" ,  y="year"
                     ,size=10
                     ,fill_color="color",fill_alpha=0.7
                     ,line_width=0
                     )
        mcglyph = plot.add_glyph(meancds,mc)
        plot.add_tools(HoverTool(tooltips = [
            ("Monthly Mean", "@year"),
            ("% Diff wrt LY", "@reldiff"),
        ] ,renderers=[mcglyph] ))
        ## axes
        addAxis(plot,"above")
        addAxis(plot,"below")
        if mo in LM :
            yticker = BasicTicker()
            yaxis = LinearAxis()
            plot.add_layout(yaxis, 'left')
        else:
            addAxis(plot,"left")
        if mo in RM:
            yticker = BasicTicker()
            yaxis = LinearAxis()
            plot.add_layout(yaxis, 'right')
        else:
            addAxis(plot,"right")

        if tooltips is not None:
            hovertool= HoverTool(tooltips=tooltips,renderers=rr)
            plot.add_tools(hovertool)
            
        plot.add_layout(Grid(dimension=0, ticker=BasicTicker()))
        plot.add_layout(Grid(dimension=1, ticker=BasicTicker()))
        if functor is not None:
            plot = functor(plot,source)
        allPlots.append( plot)
        cyc = gridplot(allPlots,ncols=3,merge_tools = True, toolbar_options={'logo': None})
    return cyc
    

yoy2= YoYADI(w,'sAdi',"14 Day Smoothed ADI")
#yoy3 = YoYADI(w,'s2Adi',"7 Day Smoothed ADI")
cyc1 = Cycle("sAdi", tooltips=[
        ("date","@date"),
        ("14 day smoothed ADI(mm)","@adi"),
        ("Year Over Year Rel Diff", "@TYvsLY"),
        ("Year Over Year Diff", "@delta")
])

# cyc3 = Cycle("sAdiCentered", tooltips=[
#         ("date","@date"),
#         ("14 day smoothed centered ADI(mm)","@adi")
# ])

def reldiffFunctor (p, cds):
    zeroline = Span(location=0,
                    dimension='width', line_color='red',
                    line_dash='dashed', line_width=1)
    p.add_layout(zeroline)
    return p
cyc2 = Cycle("reldiff",tooltips=[
        ("date","@date"),
        ("Year Over Year Rel Diff", "@TYvsLY")
    ],functor=reldiffFunctor)

from bokeh.models.widgets import Panel, Tabs
tab1 = Panel(child=cyc1, title="14 Day Smoothed ADI")
tab2 = Panel(child=cyc2, title="14 Day Smoothed YoY Change")
#tab3 = Panel(child=cyc3, title="14 Day Smoothed Centered ADI")
tabs = Tabs(tabs=[ tab1, tab2 ])

tabyoy = Tabs(tabs=[ Panel(child=yoy,title="Daily Usage With Different Measures"),
                     Panel(child=yoy2,title="14 Day smoothed ADI across years")
                     # Panel(child=yoy3,title="7 Day smoothed ADI across years")
])

plots = { 'cyctab': tabs,'yoy':tabyoy}
script, div = components(plots)
app = flask.Flask(__name__)
print(max(w['date']))
html = render_without_request(
        'templates.html',
        plot_script=script,
        plot_cyctab=div['cyctab'],
        plot_yoy=div['yoy'],
        date_computed = max(w['date']),
        js_resources=js_resources,
        css_resources=css_resources,
)
output = encode_utf8(html)
with open("index.html", "w") as text_file:
    text_file.write(output)





# w = w.assign(color = map(lambda yr: line_colors[int(yr)-2014], list(w['year'])))

# ymin,ymax = ExpandedRange([w['s2Adi']], 0.1)
# allPlots = []
# LM = ('Jan','Apr','Jul','Oct')
# RM = ('Mar','Jun','Sep','Dec')
# for mo in ('Oct','Nov',"Dec","Jul",'Aug','Sep','Apr','May','Jun','Jan',"Feb","Mar"):
#     x1 = w.loc[w['month'] == mo]
#     mbl = 0 #40 if mo in LM else 0
#     mbb = 0
#     p = figure(plot_width=int(400.0),
#                plot_height=int(0.33*400.0),
#                y_range = [ymin,ymax],
#                x_range = ExpandedRange(  [ [1.0], list( w['id'])], 0.05),
#                min_border_left=2+mbl, min_border_right=2, min_border_top=2, min_border_bottom=2+mbb,
#                tools = "")
#     p.toolbar.logo = None
#     p.toolbar_location = None
#     ## Remove bottom axis labels
#     p.xaxis[0].ticker = FixedTicker()
#     if mo not in LM:
#         p.yaxis[0].ticker = FixedTicker()
#     rightaxis = LinearAxis(axis_label=None)
#     if mo not in RM:
#         rightaxis.ticker= FixedTicker()
#     else:
#         rightaxis.ticker = BasicTicker()
#     topxaxis = LinearAxis(axis_label=None)
#     topxaxis.ticker = FixedTicker()
#     p.add_layout(rightaxis, 'right')
#     p.add_layout(topxaxis, 'above')
#     # p.title.text = mo
#     for i,yr in enumerate(('2014','2015','2016','2017')):
#         p.line('id', 's2Adi', source=x1.loc[x1['year']==yr],color=line_colors[i], line_width=2)
#     allPlots.append(p)
# cyc=gridplot(allPlots,ncols=3,merge_tools = True, toolbar_options={'logo': None})

