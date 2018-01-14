import numpy as np
import pretty_midi

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

def notes_to_lilypond(notes):
    pass # TODO

if __name__=="__main__":
    data = load_file("data/perfect.tab")
    print(data)
    tabs = extract_tabs(data)
    print(tabs)
    bars = extract_bars(tabs)
    print(bars)
    notes = extract_notes(bars)
    midi = notes_to_midi(notes, 80)
    midi.write("file.mid")
