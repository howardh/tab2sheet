import numpy as np
import os
import h5py
import pretty_midi
import dill
import itertools

def load_file(file_name):
    """
    Load the file and return a list containing each line of the file
    """
    with open(file_name,"r") as f:
        return f.readlines()

def extract_tabs(data):
    """
    Extract the lines in the data containing the tabs.
    """
    global candidates, pipe_count, hyphen_count
    # Count hyphen characters
    hyphen_percent = [s.count('-')/len(s) for s in data]
    pipe_count = [s.count('|') for s in data]

    # Must have property that six consecutive lines have same pipe count, and
    # high hyphen count.
    # TODO: For now, we'll just check that  there are hyphens there. Haven't
    # encountered any problems yet with only checking pipes
    # TODO: Could also check if the pipes are aligned.
    candidates = []
    for i in range(len(data)-5):
        if pipe_count[i] == 0:
            continue
        if any([pipe_count[i] != pipe_count[i+j] for j in range(1,6)]):
            continue
        if any([hyphen_percent[i] == 0 for j in range(1,6)]):
            continue
        candidates.append(list(range(i,i+6)))

    tabs = []
    for c in candidates:
        for c2 in c:
            tabs.append(data[c2])

    return tabs

def extract_bars(tabs):
    """
    Split the tabs bar-by-bar, and return a list of 6-tuples with each bar
    separated
    """
    if len(tabs) != 6:
        return extract_bars(tabs[:6]) + extract_bars(tabs[6:])

    bar_locations = [[i for i,x in enumerate(t) if x=='|'] for t in tabs]

    # Check for alignment
    for b in bar_locations:
        if b != bar_locations[0]:
            raise Exception("Bars not aligned. Data: %s" % tabs)

    bar_locations = bar_locations[0]

    output = []
    for i in range(len(bar_locations)-1):
        output.append([t[bar_locations[i]:bar_locations[i+1]+1] for t in tabs])

    return output

def convert_bar(bar):
    """
    Convert the human-readable bar into a more computer-friendly format
    """
    out = []
    for i in range(len(bar)):
        if bar[i] == '|':
            continue
        if bar[i].isdigit():
            if bar[i-1].isdigit():
                out.append(-1)
            else:
                if bar[i+1].isdigit():
                    out.append(int(bar[i:i+2]))
                else:
                    out.append(int(bar[i]))
        else:
            out.append(-1)
    return out

def bar_to_notes(bar, string):
    """
    Convert a human-readable bar into midi note numbers, and -1 where there are
    no notes.
    """
    starting_notes = [52,47,43,38,33,28]
    cb = convert_bar(bar)
    output = [-1 if x==-1 else starting_notes[string]+x for x in cb]
    return output

def extract_notes(bars):
    """
    Convert human-readable bars into one-dimensional lists of notes.
    If no notes are played at any given time, the value is None.

    e.g.
        Input:
            |-----------------|
            |----3-3-----3-3--|
            |----0-0-----0-0--|
            |-----------------|
            |-----------------|
            |-3-------3-------|
        Output:
            [[None, [31], None, None, [50, 43], None, [50, 43], None, None, [31], None, None, [50, 43], None, [50, 43], None, None]]
    """
    output = []
    for bar in bars:
        notes = np.array([bar_to_notes(b,i) for i,b in enumerate(bar)])

        # Flatten into a single array
        midi_notes = []
        for i in range(notes.shape[1]):
            if all(notes[:,i] == -1):
                midi_notes.append(None)
            else:
                midi_notes.append([n for n in notes[:,i] if n!=-1])
        output.append(midi_notes)
    return output

def notes_to_midi(notes, bpm):
    sample_rate = 44100
    beats_per_bar = 4
    sec_per_beat = 60/bpm
    sec_per_bar = sec_per_beat * beats_per_bar

    midi = pretty_midi.PrettyMIDI()
    guitar = pretty_midi.Instrument(program=25)
    for i,bar in enumerate(notes):
        for j,ns in enumerate(bar):
            if ns is None:
                continue
            sec_per_note = sec_per_bar/len(bar)
            bar_start = sec_per_bar*i
            for note_number in ns:
                note = pretty_midi.Note(velocity=100, pitch=note_number,
                        start=bar_start+sec_per_note*j,
                        end=bar_start+sec_per_note*(j+1))
                guitar.notes.append(note)
    midi.instruments.append(guitar)
    return midi

def compute_note_durations(notes):
    num_notes = 0
    for n in notes:
        if n is not None:
            num_notes += 1
    subdivisions = 2
    while subdivisions < num_notes:
        subdivisions *= 2
    subdivisions *= 2

    if notes[0] is None:
        notes = notes[1:]

    boxes = [None]*subdivisions
    for i,n in enumerate(notes):
        if n is None:
            continue
        closest_box = int(i/len(notes)*subdivisions)
        # TODO: This loop could potentially go out of bounds. If that happens,
        # we'd need to increase the number of boxes, and try again
        while True:
            if boxes[closest_box] is None:
                boxes[closest_box] = n
                break
            else:
                closest_box += 1

    # Convert to counts
    durations = [None]*len(boxes)
    count = 1
    for i in range(len(boxes)-1,-1,-1):
        if boxes[i] is None:
            count += 1
        else:
            durations[i] = count
            count = 1
    if boxes[0] is None:
        durations[0] = count

    return durations

def bar_to_lilypond_duration(durations):
    """
    Take a list of notes durations from compute_note_durations() from a single bar, and convert it
    into a string representing it in Lilypond notation.
    """
    size = len(durations)
    durations = [d for d in durations if d is not None]
    # Convert to lilypond note durations
    def is_pow2(n):
        return ((n & (n-1)) == 0)
    def compute_lp_duration(d,s):
        # If it's a power of 2
        if is_pow2(d):
            return str(int(size/d))
        # If it's a multiple of 3
        if d%3 == 0:
            if is_pow2(int(d/3)):
                return str(int(size/(d/3*2)))+"."
        # Otherwise, it's a tied note. Split into factors.
        # Test all possible splittings
        for i in range(1,int(d/2)+1):
            d1 = compute_lp_duration(d-i,s)
            d2 = compute_lp_duration(i,s)
            if d1 is None or d2 is None:
                continue
            if type(d1) is not list:
                d1 = [d1]
            if type(d2) is not list:
                d2 = [d2]
            return d1+d2
        return None
    lp_durations = [compute_lp_duration(d,size) for d in durations]
    return lp_durations

notes = ["aes","a","bes","b","c","des","d","ees","e","f","ges","g"]
octaves = [",,,",",,",",","","'","''","'''"]
all_notes = [n+o for o,n in itertools.product(octaves,notes)]
def midi_to_lilypond_note(note):
    """
    Convert an integer midi note number into a lilypond note string.
    """
    return all_notes[note+4]

def bar_to_lilypond_notes(notes):
    """
    Take a list of notes from extract_notes() and convert them into a list of
    lilypond notes.
    """
    lp_notes = []
    if notes[0] is None:
        notes = notes[1:]
    if notes[0] is None:
        lp_notes.append("r")
    for n in notes:
        if n is None:
            continue
        if type(n) is list:
            lp_notes.append([midi_to_lilypond_note(x) for x in n])
        else:
            lp_notes.append(midi_to_lilypond_note(n))
    return lp_notes

def bar_to_lilypond(bar):
    notes = extract_notes([bar])[0]
    durations = compute_note_durations(notes)
    lpd = bar_to_lilypond_duration(durations)
    lpn = bar_to_lilypond_notes(notes)
    output = ""
    for n,d in zip(lpn,lpd):
        if type(n) is list:
            if len(set(n)) != 1:
                n = ["<%s>"%" ".join(set(n))]
        if type(d) is list:
            for x in d:
                output += "~"+n[0]+x+" "
        else:
            output += n[0]+d+" "
    return output

def file_to_lilypond(file_name):
    data = load_file("data/stairway.tab")
    tabs = extract_tabs(data)
    bars = extract_bars(tabs)
    score = ""
    for b in bars:
        lp = bar_to_lilypond(b)
        score += lp + "\n"
    output = ("\score{"
              "{%s}"
              "\layout{}"
              "\midi{}"
              "}")%score
    return output

if __name__=="__main__":
    lp = file_to_lilypond("data/stairway.tab")
    print(lp)
