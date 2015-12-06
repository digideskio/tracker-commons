# -*- coding: utf-8 -*-
"""
WCON Parser

This parser accepts any valid WCON file, but the output is always "canonical"
WCON, which makes specific choices about how to arrange and format the WCON
file.  This way the functional equality of any two WCON files can be tested 
by this:

w1 = WCONWorm.load('file1.wcon')
w2 = WCONWorm.load('file2.wcon')

assert(w1 == w2)

# or:

w1.output('file1.wcon')
w2.output('file2.wcon')

import filecmp
assert(filecmp.cmp('file1.wcon', file2.wcon'))

"""

import pdb
import warnings
import itertools
import json
import numpy as np
import pandas as pd

from io import StringIO

from measurement_unit import MeasurementUnit

def reject_duplicates(ordered_pairs):
    """Reject duplicate keys."""
    unique_dict = {}
    for key, val in ordered_pairs:
        if key in unique_dict:
           raise KeyError("Duplicate key: %r" % (key,))
        else:
           unique_dict[key] = val

    return unique_dict


def restore(dct):
    """
    """

    if "py/dict" in dct:
        return dict(dct["py/dict"])
    if "py/tuple" in dct:
        return tuple(dct["py/tuple"])
    if "py/set" in dct:
        return set(dct["py/set"])
    if "py/collections.namedtuple" in dct:
        data = dct["py/collections.namedtuple"]
        return namedtuple(data["type"], data["fields"])(*data["values"])
    if "py/numpy.ndarray" in dct:
        data = dct["py/numpy.ndarray"]
        return np.array(data["values"], dtype=data["dtype"])
    if "py/collections.OrderedDict" in dct:
        return OrderedDict(dct["py/collections.OrderedDict"])
    return dct


def get_mask(arr, desired_key):
    """
    In an array of dicts, obtain a mask on arr of elements having 
    the desired key
    
    Parameters
    ----------
    arr: list-like array of dicts
    desired_key: str
    
    Returns
    ----------
    Boolean numpy array of same size as arr
    
    """
    # Find elements having a time aspect
    desired_indexes = [i for (i,s) in enumerate(arr) if desired_key in s]
    desired_indexes = np.array(desired_indexes)

    # Transform our list of indexes into a mask on the data array
    return np.bincount(desired_indexes, minlength=len(arr)).astype(bool)



class WormData():
    """
    A worm's data (stripped of units and metadata)

    Time-series and aggregate data
    Tagged by worm or tagged by plate    
    
    Attributes
    -------------
    time_df: Pandas DataFrame
        Indexed by time
        All worms
        Plate data uses id:'plate'
    
    
    """
    pass


class WCONWorm():
    """
    A worm as specified by the WCON standard

    Attributes
    -------------
    units: dict
        May be empty, but is never None since 'units' is required 
        to be specified.
    metadata: dict
        If 'metadata' was not specified, metadata is None.
        The values in this dict might be nested into further dicts or other
        data types.
    data: Pandas DataFrame or None
        If 'data' was not specified, data is None.

    Usage
    -------------
    # From a file:
    with open('my_worm.wcon', 'r') as infile:
        w1 = WCONWorm.load(infile)
    
    # From a string literal:
    from io import StringIO
    w2 = WCONWorm.load(StringIO('{"tracker-commons":true, '
                                '"units":{},"data":{}}'))

    Custom WCON versions
    --------------------
    
    Any top-level key other than the basic:
    
    - tracker-commons
    - files
    - units
    - metadata
    - data
    
    Is assigned to the dictionary object special_root
    
    To process these items, this class should be subclassed and this method
    overwritten.
    
    """
    basic_keys = ['tracker-commons', 'files', 'units', 'metadata', 'data']

    @classmethod
    def merge(w1, w2):
        """
        Merge two worm files
        Any clashing data found will cause an exception to be raised.
        
        """
        # TODO
        pass

    def load_from_file(cls, JSON_path, 
                       load_prev_chunks=True, 
                       load_next_chunks=True):
        """
        Factory method returning a merged WCONWorm instance of all chunks.

        Uses recursion if there are multiple chunks.
        
        Parameters
        -------------
        JSON_path: a file path to a file that can be opened
            
        load_prev_chunks: bool
            If a "files" key is present, load the previous chunks and merge
            them with this one.  If not present, return only the current 
            file's worm.

        load_next_chunks: bool
            If a "files" key is present, load the next chunks and merge
            them with this one.  If not present, return only the current 
            file's worm.

        """
        print("Loading file: " + JSON_path)

        with open(JSON_path, 'r') as infile:
            w_current = cls.load(infile)

        # e.g. cur_filename = 'filename_2.wcon'
        # cur_ext = '_2', prefix = 'filename', suffix = '.wcon'
        cur_filename = JSON_path
        cur_ext = w_current.files['this']
        if cur_filename.find(cur_ext) == -1:
            raise AssertionError('Cannot find the current extension "'
                                 + cur_ext + '" within the current filename "'
                                 + cur_filename + '".')
        prefix = cur_filename[:cur_filename.find(cur_ext)]
        suffix = cur_filename[cur_filename.find(cur_ext)+len(cur_ext):]
        
        # If we are supposed to load the previous chunks, and one exists, 
        # load it and merge it with the current chunk
        if (load_prev_chunks and 
            not w_current.files is None and 
            not w_current.files['prev'] is None):
                prev_file_name = prefix + w_current.files['prev'][0] + suffix
                w_prev = cls.load_from_file(prev_file_name,
                                            load_prev_chunks=True,
                                            load_next_chunks=False)
                w_current = cls.merge(w_current, w_prev)

        # Same with the next chunks
        if (load_next_chunks and 
            not w_current.files is None and 
            not w_current.files['next'] is None):
                next_file_name = prefix + w_current.files['next'][0] + suffix
                w_next = cls.load_from_file(next_file_name,
                                            load_prev_chunks=False,
                                            load_next_chunks=True)
                w_current = cls.merge(w_current, w_next)

        return w_current
        


    @classmethod
    def load(cls, JSON_stream):
        """
        Factory method to create a WCONWorm instance
        
        This does NOT load chunks, because a file stream does not 
        have a file name.  In order to load chunks, you must invoke the
        factory method load_from_file.  You will be passing it a file path 
        from which it can find the other files/chunks.
        
        Parameters
        -------------
        JSON_stream: a text stream implementing .read()
            e.g. an object inheriting from TextIOBase
                    
        """
        w = cls()
        serialized_data = JSON_stream.read()

        # Load the whole JSON file into a nested dict.  Any duplicate
        # keys raise an exception since we've hooked in reject_duplicates
        root = json.loads(serialized_data, object_hook=restore,
                          object_pairs_hook=reject_duplicates)
    
        if 'files' in root:
            w.files = w['files']
        else:
            w.files = None
    
        # ===================================================
        # BASIC TOP-LEVEL VALIDATION
        
        if not ('tracker-commons' in root):
            warnings.warn('{"tracker-commons":true} was not present. '
                          'Nevertheless proceeding under the assumption '
                          'this is a WCON file.')
        
        if 'tracker-commons' in root and root['tracker-commons'] == False:
            raise AssertionError('"tracker-commons" is set to false.')
    
        # ===================================================
        # HANDLE THE BASIC TAGS: 'units', 'metadata', 'data'    
    
        if not 'units' in root:
            raise AssertionError('"units" is required')
        else:
            w.units = root['units']
            
            for key in w.units:
                w.units[key] = MeasurementUnit(w.units[key])
        
        if not 'data' in root:
            # The WCON specification requires the data field to be present
            raise AssertionError('"data" is required')
        elif len(root['data']) > 0:
            w.data = w._parse_data(root['data'])
            
            # Shift the coordinates by the amount in the offsets 'ox' and 'oy'
            w._convert_origin()
        else:
            # "data": {}
            w.data = None

        if 'metadata' in root:
            w.metadata = w._parse_metadata(root['metadata'])
        else:
            w.metadata = None
        
        # ===================================================    
        # Any special top-level keys are sent away for later processing
        w.special_keys = [k for k in root.keys() if k not in w.basic_keys]
        if w.special_keys:
            w.special_root = {k: root[k] for k in w.special_keys}

        # DEBUG: temporary
        w.root = root

        return w


    def _parse_metadata(self, metadata):
        """
        Parse the 'metadata' element
        
        Return an object encapsulating that data
        
        """
        return metadata

    def _parse_data(self, data):
        """
        Parse the 'data' element
        
        Return an object encapsulating that data
        
        """
        # If data is single-valued, wrap it in a list so it will be just
        # a special case of the array case.
        if type(data) == dict:
            data = [data]

        data = np.array(data)

        # "Aspect" is my term for the articulation points at a given time frame
        # So if you track 49 skeleton points per frame, then x and y have
        # 49 aspects per frame, but ox is only recorded once per frame, or
        # even once across the whole video.
        elements_with_aspect = ['x', 'y']
        elements_without_aspect = ['ox', 'oy', 'head', 'ventral']
        basic_data_keys = elements_with_aspect + elements_without_aspect
        supported_data_keys = basic_data_keys + ['id', 't']

        # Get a list of all ids in data
        ids = list(set([x['id'] for x in data if 'id' in x]))

        is_time_series_mask = get_mask(data, 't')
        has_id_mask = get_mask(data, 'id')

        # Time-series data goes into this Pandas DataFrame
        # The dataframe will have t as index, and multilevel columns
        # with id at the first level and all other keys at second level.
        time_df = None

        # Clean up and validate all time-series data segments
        for data_segment in data[is_time_series_mask]:
            segment_keys = [k for k in data_segment.keys() if k != 'id']

            # If the 't' element is single-valued, wrap it and all other
            # elements into an array so single-valued elements
            # don't need special treatment in our later processing steps
            if type(data_segment['t']) != list:
                for subkey in segment_keys:
                    data_segment[subkey] = [data_segment[subkey]]

            # Further, we have to wrap the elements without an aspect
            # in a further list so that when we convert to a dataframe,
            # our staging data list comprehension will be able to see
            # everything as a list and not as single-valued
            for subkey in elements_without_aspect:
                if subkey in data_segment:
                    if type(data_segment[subkey]) != list:
                        data_segment[subkey] = [[data_segment[subkey]]]
                    else:
                        data_segment[subkey] = [[x] for x in data_segment[subkey]]

            subelement_length = len(data_segment['t'])

            # Broadcast aspectless elements to be 
            # length n = subelement_length if it's 
            # just being shown once right now  (e.g. for 'ox', 'oy', etc.)
            for k in elements_without_aspect:
                if k in segment_keys:
                    k_length = len(data_segment[k])
                    if k_length not in [1, subelement_length]:
                        raise AssertionError(k + " for each segment "
                                             "must either have length 1 or "
                                             "length equal to the number of "
                                             "time elements.")
                    elif k_length == 1:
                        # Broadcast the origin across all time points
                        # in this segment
                        data_segment[k] = data_segment[k] * subelement_length
            
            # Validate that all sub-elements have the same length
            subelement_lengths = [len(data_segment[key]) 
                                  for key in segment_keys]

            # Now we can assure ourselves that subelement_length is 
            # well-defined; if not, raise an error.
            if len(set(subelement_lengths)) > 1:
                raise AssertionError("Error: Subelements must all have "
                                     "the same length.")

            
            # Now let's validate that each subsubelement with aspect are 
            # same-sized
            for i in range(subelement_length):
                # The x and y arrays for element i of the data segment
                # must have the same length
                subsubelement_lengths = [len(data_segment[k][i]) for k in 
                                         elements_with_aspect]
                
                if len(set(subsubelement_lengths)) > 1:
                    raise AssertionError("Error: x and y, etc. must have same "
                                         "length for index " + str(i))
                else:
                    aspect_size = subsubelement_lengths[0]


        # Obtain a numpy array of all unique timestamps used
        timeframes = []
        for data_segment in data[is_time_series_mask]:
            timeframes.extend(data_segment['t'])
        timeframes = np.array(list(set(timeframes)))


        # Consider only time-series data stamped with an id:
        for data_segment in data[is_time_series_mask & has_id_mask]:
            # Add this data_segment to a Pandas dataframe
            segment_id = data_segment['id']
            segment_keys = np.array([k for k in data_segment.keys() 
                                       if not k in ['t','id']])
            
            cur_timeframes = np.array(data_segment['t'])

            # Create our column names as the cartesian product of
            # the segment's keys and the id of the segment
            # Only elements articulated across the skeleton, etc, of the worm
            # have the "aspect" key though
            cur_elements_with_aspect = [k for k in elements_with_aspect
                                                if k in segment_keys]
            cur_elements_without_aspect = [k for k in elements_without_aspect
                                                if k in segment_keys]
            key_combos = list(itertools.product([segment_id], 
                                                cur_elements_with_aspect,
                                                range(aspect_size)))
            key_combos.extend(
                         list(itertools.product([segment_id], 
                                                cur_elements_without_aspect, 
                                                [0]))
                             )

            column_type_names = ['id', 'key', 'aspect']
            cur_columns = pd.MultiIndex.from_tuples(key_combos,
                                                    names=column_type_names)

            # e.g. if this segment has only 'x', 'y', that's what we'll be 
            # looking to add to our dataframe data staging in the next step
            cur_data_keys = [k for k in basic_data_keys if k in data_segment.keys()]
  
            # Stage the data for addition to our DataFrame.
            # Shape KxI where K is the number of keys and 
            #                 I is the number of "aspects"
            cur_data = np.array(
                  [np.concatenate(
                                  [data_segment[k][i] for k in cur_data_keys]
                                 ) for i in range(len(cur_timeframes))]
                               )


            cur_df = pd.DataFrame(cur_data, columns=cur_columns)

            cur_df.index = cur_timeframes
            cur_df.index.names = 't'

            # We want the index (time) to be in order.
            cur_df.sort_index(axis=0, inplace=True)
            
            # Apparently multiindex must be sorted to work properly:
            cur_df.sort_index(axis=1, inplace=True)
            
            if time_df is None:
                time_df = cur_df
            else:
                time_df.sort_index(axis=1, inplace=True)
                # Append cur_df to time_df

                # Add all rows that don't currently exist in time_df
                time_df = pd.concat([time_df, cur_df[~cur_df.index.isin(time_df.index)]])

                time_df.sort_index(axis=1, inplace=True)

                # Obtain a sliced version of time_df, showing only
                # the columns and rows shared with the cur_df
                time_df_sliced = \
                    time_df.loc[time_df.index.isin(cur_df.index),
                                time_df.columns.isin(cur_df.columns)]

                cur_df_sliced = \
                    cur_df.loc[cur_df.index.isin(time_df.index),
                               cur_df.columns.isin(time_df.columns)]

                # Sort our slices so they will be lined up for comparison
                time_df_sliced.sort_index(inplace=True)
                cur_df_sliced.sort_index(inplace=True)                                                    

                # Obtain a mask of the conflicts in the current segment
                # as compared with all previously loaded data.  That is:
                # NaN NaN = False
                # NaN 2   = False
                # 2   2   = False
                # 2   3   = True
                # 2   NaN = True
                data_conflicts = (pd.notnull(time_df_sliced) & 
                                  (time_df_sliced != cur_df_sliced))

                if data_conflicts.any().any():
                    raise AssertionError("Data from this segment conflicted "
                                         "with previously loaded data:\n", 
                                         data_conflicts)

                # Replace any rows that do exist with the cur_df version
                time_df.update(cur_df)
                
                # TODO: concatenate using a list comprehension as calling it
                # iteratively like this causes a performance hit (see
                # http://pandas.pydata.org/pandas-docs/stable/merging.html#concatenating-objects
                # "Note It is worth noting however, that concat (and therefore append) 
                # makes a full copy of the data, and that constantly reusing this 
                # function can create a signifcant performance hit. If you need 
                # to use the operation over several datasets, use a list comprehension."


        # We want the index (time) to be in order.
        time_df.sort_index(axis=0, inplace=True)

        return time_df


    def _convert_origin(self):
        """
        Add the offset values 'ox' and 'oy' to the 'x' and 'y' 
        coordinates in the dataframe

        Offset values that are NaN are considered to be zero.
        
        After this is done, set all offset values to zero.
        
        """
        for worm_id in self.data.columns.get_level_values(0).unique():
            cur_worms = self.data.loc[:,(worm_id)]

            for offset, coord in zip(['ox', 'oy'], ['x', 'y']):
                if offset in cur_worms.columns.get_level_values(0):
                    all_x_columns = cur_worms.loc[:,(coord)]
                    ox_column = cur_worms.loc[:,(offset)].fillna(0)
                    affine_change = (np.array(ox_column) * 
                                     np.ones(all_x_columns.shape))
                    # Shift our 'x' values by the amount in 'ox'
                    all_x_columns += affine_change
                    self.data.loc[:,(worm_id,coord)] = all_x_columns.values
                    
                    # Now reset our 'ox' values to zero.
                    self.data.loc[:,(worm_id,offset)] = \
                                                    np.zeros(ox_column.shape)


pd.set_option('display.expand_frame_repr', False)


if __name__ == '__main__1':

    JSON_path = '../../tests/hello_world_simple.wcon'

    with open(JSON_path, 'r') as infile:
        w1 = WCONWorm.load(infile)
    
    u = MeasurementUnit('cm')

    
if __name__ == '__main__':
    WCON_string1 = \
        """
        {
            "tracker-commons":true,
            "metadata":{
                   "lab":{"location":"CRB, room 5020", "name":"Behavioural Genomics" },
                   "who":"Firstname Lastname",
                   "timestamp":"2012-04-23T18:25:43.511Z",
                   "temperature":{ "experiment":22, "cultivation":20, "units":"C" },
                   "humidity":{ "value":40, "units":"%" },
                   "dish":{ "type":"petri", "size":35, "units":"mm" },
                   "food":"none",
                   "media":"agarose",
                   "sex":"hermaphrodite",
                   "stage":"adult",
                   "age":"18:25:43.511",
                   "strain":"CB4856",
                   "image_orientation":"imaged onto agar or imaged through agar",
                   "protocol":"text description of protocol",
                   "software":{
                        "tracker":{ "name":"Software Name", "version":1.3 },
                        "featureID":"@OMG"
                   },
                   "settings":"Any valid JSON entry with hardware and software configuration can go here"
            },
            "units":{"t":"s", "x":"mm", "y":"mm"},
            "data":[
                { "id":1, "t":1.3, "x":[7.2, 5], "y":[0.5, 0.86] }
            ]                
        }        
        """
    w1 = WCONWorm.load(StringIO(WCON_string1))

if __name__ == '__main__3':
    w1 = WCONWorm.load(StringIO('{"tracker-commons":true, "units":{},'
                                '"data":[{"id":3, "t":1.3, '
                                         '"x":[3,4,4,3.2], '
                                         '"y":[5.4,3,1,-3]}]}'))


# Suppress RuntimeWarning warnings in Spider because it's a known bug
# http://stackoverflow.com/questions/30519487/
warnings.simplefilter(action = "ignore", category = RuntimeWarning)
