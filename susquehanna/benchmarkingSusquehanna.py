
# coding: utf-8

# # Making flood contingency figures (colored) and statistics

# This notebook compares two flood maps and computes hit rate, miss rate, FAR, and correct negatives. IT also prepares a nice looking map over the target area. The following is done:
# - resampling maps to the same resolution (e.g. using the extent of the smallest map, or the mask/clone map)
# - masking values with a zero-one map, i.e. mask out values in areas where a flood model is not computing anything
# - establishing a 1-2-3 map (indicating where either one of the maps gives a hit, or all maps give a hit
# - computing the typical contingency scores
# 
# The notebook uses the hydrotools package for reading data and some of the plotting functions
# (obtain it from ...)

# ## packages

# In[2]:

#~ get_ipython().magic(u'pylab inline')
import numpy as np
from hydrotools import gis
import gdal
import matplotlib.pyplot as plt
from matplotlib import colors
import gdal


# ## Functions

# In[3]:

def read_axes(fn):
    """
    Retrieve x and y ax from a raster datasets (GDAL compatible)
    """
    ds = gdal.Open(fn)
    geotrans = ds.GetGeoTransform()
    originX = geotrans[0]
    originY = geotrans[3]
    resX = geotrans[1]
    resY = geotrans[5]
    cols = ds.RasterXSize
    rows = ds.RasterYSize
    x = np.linspace(originX+resX/2, originX+resX/2+resX*(cols-1), cols)
    y = np.linspace(originY+resY/2, originY+resY/2+resY*(rows-1), rows)
    ds = None
    return x, y


# In[4]:

def contingency_map(array1, array2, threshold1=0., threshold2=0.):
    """
    Establish the contingency between array1 and array2.
    Returns an array where 
    1 means only array2 gives a value > threshold1, 
    2 means only array1 gives a values > threshold2,
    3 means array1 gives a value > threshold1, and array2 a value > threshold2
    0 means both arrays do not give a value > threshold1, 2 respectively
    
    function returns the threshold exceedance (0-1) of array 1 and 2, as well as the contingency map
    """
    array1_thres = array1 > threshold1
    array2_thres = array2 > threshold2
    contingency = np.zeros(array1.shape)
    contingency += np.int16(array2_thres)
    contingency += np.int16(array1_thres)*2
    return array1_thres, array2_thres, contingency


# In[5]:

def hit_rate(array1, array2):
    """
    calculate the hit rate based upon 2 boolean maps. (i.e. where are both 1)
    """
    # count the number of cells that are flooded in both array1 and 2
    idx_both = np.sum(np.logical_and(array1, array2))
    idx_1 = np.sum(array1)
    return float(idx_both)/float(idx_1)


# In[6]:

def false_alarm_rate(array1, array2):
    """
    calculate the false alarm rate based upon 2 boolean maps. (i.e. amount of cells where array2 is True but array1 False)
    """
    # count the number of cells that are flooded in both array1 and 2
    idx_2_only = np.sum(np.logical_and(array2, array1!=1))
    idx_2_total = np.sum(array2)
    
    return float(idx_2_only)/float(idx_2_total)


# In[7]:

def critical_success(array1, array2):
    """
    calculate the critical success rate based upon 2 boolean maps. 
    """
    idx_both = np.sum(np.logical_and(array1, array2))
    idx_either = np.sum(np.logical_or(array1, array2))
    return float(idx_both)/float(idx_either)


# In[53]:

def plot_contingency(x, y, contingency, title):
    """
    Prepare a geographical map of a contingency score map, with appropriate coloring
    """
    import cartopy.crs as ccrs
    from cartopy.mpl.gridliner import LONGITUDE_FORMATTER, LATITUDE_FORMATTER
    import cartopy
    from matplotlib import colors
    from cartopy.io.img_tiles import StamenTerrain
    import matplotlib.pyplot as plt
    plot_image = np.ma.masked_where(contingency==0, contingency)
    extent = (x.min(), x.max(), y.min(), y.max())
    cmap = colors.ListedColormap(['blue', 'red', 'green'])
    bounds=[0.5, 1.5, 2.5, 3.5]
    norm = colors.BoundaryNorm(bounds, cmap.N)

    tiler = StamenTerrain()
    mercator = tiler.crs
    fig =plt.figure(figsize=(10,10))
    ax = fig.add_subplot(111, axisbg='None', projection=mercator) # mercator
    # get hold of the coastlines for that area.
#     ax.add_feature(cartopy.feature.LAND, zorder=1)
#     ax.add_feature(cartopy.feature.OCEAN, zorder=1)
#     ax.add_feature(cartopy.feature.COASTLINE)
#     ax.add_feature(cartopy.feature.BORDERS, linestyle=':')
#     ax.add_feature(cartopy.feature.LAKES, alpha=0.5)
#     ax.add_feature(cartopy.feature.RIVERS)
#     ax.stock_img()
    ax.set_extent(extent)
    gl = ax.gridlines(crs=ccrs.PlateCarree(), draw_labels=True,
                      linewidth=1, color='gray', alpha=0.5, linestyle='--')
#     ax.background_patch.set_fill(False)
    ax.add_image(tiler, 9, zorder=1)
    img = ax.imshow(plot_image, extent=extent, vmin=1., vmax=3., interpolation='nearest', 
                        cmap=cmap, norm=norm, zorder=3, transform=ccrs.PlateCarree())  # origin='lower', transform=mercator
    ax.set_xlabel('longitude')
    ax.set_ylabel('latitude')


    # make a color bar
    cbar = plt.colorbar(img, cmap=cmap, norm=norm, boundaries=bounds, ticks=[1, 2, 3], orientation='horizontal')

    cbar.ax.set_xticklabels(['Global only', 'Local only', 'Both'])
    fig.suptitle(title, fontsize=14)
    fig.savefig('{:s}.png'.format(title), bbox_inches='tight', dpi=300)


# In[56]:

def contingency_default(bench_fn, model_fn, bench_thres, model_thres, mask_fn, title, masking=False):
    print('Warping {:s}'.format(mask_fn))
    print('Warping {:s}'.format(model_fn))
    gis.gdal_warp(bench_fn, model_fn, 'temp1.tif', gdal_interp=gdal.GRA_Average)
    gis.gdal_warp(mask_fn, model_fn, 'temp2.tif', gdal_interp=gdal.GRA_NearestNeighbour)
    x, y, bench, fill_bench = gis.gdal_readmap('temp1.tif', 'GTiff')
    x, y, model, fill_model = gis.gdal_readmap(model_fn, 'GTiff')
    x, y, mask, fill_mask = gis.gdal_readmap('temp2.tif', 'GTiff')
#     else:
#         bench = np.ma.masked_where(bench==fill_bench, bench)
#         model = np.ma.masked_where(model==fill_model, model)
    bench[bench==fill_bench] = 0.
    model[model==fill_model] = 0.
    if masking:
        bench = np.ma.masked_where(mask==255, bench)
        model = np.ma.masked_where(mask==255, model)
        
    flood1, flood2, cont_arr = contingency_map(bench, model, threshold1=bench_thres, threshold2=model_thres)
    if masking:
        cont_arr = np.ma.masked_where(mask==255, cont_arr)
    hr = hit_rate(flood1, flood2)
    far = false_alarm_rate(flood1, flood2)
    csi = critical_success(flood1, flood2)
    return hr, far, csi, x, y, cont_arr, flood1, flood2


def contingency(bench_fn, model_fn, bench_thres, model_thres, mask_fn, title, masking=False, clone_map=None):

    print('Warping {:s}'.format(bench_fn))
    gis.gdal_warp(bench_fn, clone_map, 'bench.tif', gdal_interp=gdal.GRA_NearestNeighbour)
    x, y, bench, fill_bench = gis.gdal_readmap("bench.tif", 'GTiff')

    print('Warping {:s}'.format(model_fn))
    gis.gdal_warp(model_fn, clone_map, 'model.tif', gdal_interp=gdal.GRA_NearestNeighbour)
    x, y, model, fill_model = gis.gdal_readmap('model.tif', 'GTiff')

    print('Warping {:s}'.format(mask_fn))
    gis.gdal_warp(mask_fn, clone_map, 'mask.tif', gdal_interp=gdal.GRA_NearestNeighbour)
    x, y, mask, fill_mask = gis.gdal_readmap("mask.tif", 'GTiff')

    print('Warping {:s}'.format(urban_fn))
    gis.gdal_warp(urban_fn, clone_map, 'urban.tif', gdal_interp=gdal.GRA_NearestNeighbour)
    x, y, urban, fill_urban = gis.gdal_readmap('urban.tif', 'GTiff')

    bench[bench==fill_bench] = 0.
    # added by Edwin: Ignore areas/cells belonging to permanent water bodies
    bench[model==fill_model] = 0.

    model[model==fill_model] = 0.

    if masking:
        bench = np.ma.masked_where(mask==255, bench)
        model = np.ma.masked_where(mask==255, model)
        
    flood1, flood2, cont_arr = contingency_map(bench, model, threshold1=bench_thres, threshold2=model_thres)
    if masking:
        cont_arr = np.ma.masked_where(mask==255, cont_arr)
    
    hr = hit_rate(flood1, flood2)
    far = false_alarm_rate(flood1, flood2)
    csi = critical_success(flood1, flood2)
    return hr, far, csi, x, y, cont_arr, flood1, flood2



# ## files and run

# In[65]:

# glofris downscaling output
model_fn     = r'c:\Users\hcwin\OneDrive\IVM\2017\paper_costs\benchmarks\Susquehanna\inun_susquehanna_100.tif'
#~ model_fn  = "input_data/inun_susquehanna_100.tif"
model_fn     = "/scratch-shared/edwinsut/finalizing_downscaling/using_strahler_order_1/global/maps/inun_100-year_of_channel_storage_catch_01.tif.map.masked_out.map"
model_fn     = "/scratch-shared/edwinsut/finalizing_downscaling/using_strahler_order_2/global/maps/inun_100-year_of_channel_storage_catch_02.tif.map.masked_out.map"

bench_fn  = "input_data/susquehanna_1in100.tif" # r'c:\Users\hcwin\OneDrive\IVM\2017\paper_costs\benchmarks\Susquehanna\susquehanna_1in100.tif'

# mask_fn = r'c:\Users\hcwin\OneDrive\IVM\2017\paper_costs\benchmarks\Bangladesh\mask.tif'
mask_fn   = r'c:\Users\hcwin\OneDrive\IVM\2017\paper_costs\benchmarks\Susquehanna\mask_susquehanna.tif'
mask_fn   = "input_data/mask_susquehanna.tif"

clone_map = "input_data/inun_susquehanna_100.tif"

urban_fn = mask_fn

model_warp_fn = None # r'c:\Users\hcwin\OneDrive\projects\1209884_GFRA\benchmark\inun_dynRout_RP_00100_warp.tif'

title = "Susquehanna"
hr, far, csi, x, y, cont_arr, flood1, flood2 = contingency(bench_fn, model_fn, 0.25, 0., mask_fn, title, masking = True, clone_map = clone_map)

#~ hr, far, csi, x, y, cont_arr, flood1, flood2 = contingency(bench_fn, model_fn, 0.25, 0., mask_fn, title, masking=True)


# In[66]:

plt.figure(figsize=(12, 12))
plt.imshow(cont_arr)


# In[67]:

flood2.shape


# In[68]:

print('Scores without urban mask')
print('Hit rate: {:f}'.format(hr))
print('False Alarm rate: {:f}'.format(far))
print('Critical success index: {:f}'.format(csi))


# In[69]:

plot_contingency(x, y, np.flipud(cont_arr), 'Susquehanna')
plt.savefig('Susquehanna.png', dpi=300, bbox_inches='tight')


#~ # In[27]:
#~ 
#~ hr, far, csi, x, y, cont_arr_mask, flood1, flood2 = contingency(bench_fn, model_fn, 0., 0., mask_fn, title, masking=True)
#~ print('Scores WITH urban mask')
#~ print('Hit rate: {:f}'.format(hr))
#~ print('False Alarm rate: {:f}'.format(far))
#~ print('Critical success index: {:f}'.format(csi))
#~ 
#~ 
#~ # In[28]:
#~ 
#~ plot_contingency(x, y, np.flipud(cont_arr_mask), 'Susquehanna')
#~ plt.savefig('Susquehanna.png', dpi=300, bbox_inches='tight')
#~ 
#~ 
#~ # In[10]:
#~ 
#~ import gdal
#~ gdal.GRA_NearestNeighbour
#~ 
#~ 
#~ # In[ ]:
#~ 
#~ 
#~ 
