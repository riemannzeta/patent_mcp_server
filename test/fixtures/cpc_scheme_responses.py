"""Fixtures for the CPC scheme client.

Trimmed from the live https://www.uspto.gov/web/patents/classification/cpc/html/cpc-G06N.html
on 2026-09-26: the subclass header, main group 3/00 with a nested run of
subgroups (including a brace-wrapped CPC-only title), and main group 20/00.
Markup per entry is verbatim apart from removed tooltip/notes clutter.
"""

MOCK_CPC_G06N_PAGE = """
<html><body>
<table class="classItem subslasslt8" id="G06N"><tr><td></td><td></td><td></td>
<td><div class="schemeVersion">CPC</div></td><td><div class="schemeText">COOPERATIVE PATENT CLASSIFICATION</div></td></tr>
<tr><td><a href="defG06N.html"><span class="has-def"></span></a></td><td class="note-warning-indicator"></td><td></td>
<td class="symbol"><div><span class="symbol"><span class="alink">G06N</span></span></div></td>
<td><div><div class="class-title"><span class="ipc-text">COMPUTING ARRANGEMENTS BASED ON SPECIFIC COMPUTATIONAL MODELS</span><span class="date-revised"> [2018-01]</span></div></div></td></tr></table>
<div class="toggleOn" id="G06N-5"><div class="toggleOn" id="G06N3_00-6">
<table class="classItem subclass8" id="G06N3/00"><tr><td></td><td class="note-warning-indicator"></td><td></td>
<td class="symbol"><div><span class="symbol"><span class="alink">G06N&nbsp;3/00</span></span></div></td>
<td><div><div class="class-title"><span class="ipc-text">Computing arrangements based on biological models</span><span class="date-revised"> [2022-01]</span></div></div></td></tr></table>
<div class="toggleOn" id="G06N3_00-7">
<table class="classItem subclassgt8" id="G06N3/002"><tr><td></td><td></td><td></td>
<td class="symbol"><div><span class="symbol"><span class="alink">G06N&nbsp;3/002</span></span></div></td>
<td width="20" title="Indent level is 1"><div><span class="indent"><b>. </b></span></div></td>
<td><div><div class="class-title"><span class="cpc-specific-text"><span class="sbracket">{</span><span class="cpc-text">Biomolecular computers, i.e. using biomolecules, proteins, cells</span><span class="sbracket">}</span></span><span class="date-revised"> [2013-01]</span></div></div></td></tr></table>
<table class="classItem subclassgt8" id="G06N3/02"><tr><td></td><td></td><td></td>
<td class="symbol"><div><span class="symbol"><span class="alink">G06N&nbsp;3/02</span></span></div></td>
<td width="20" title="Indent level is 1"><div><span class="indent"><b>. </b></span></div></td>
<td><div><div class="class-title"><span class="ipc-text">Neural networks</span><span class="date-revised"> [2006-01]</span></div></div></td></tr></table>
<table class="classItem subclassgt8" id="G06N3/04"><tr><td></td><td></td><td></td>
<td class="symbol"><div><span class="symbol"><span class="alink">G06N&nbsp;3/04</span></span></div></td>
<td width="20" title="Indent level is 2"><div><span class="indent"><b>. . </b></span></div></td>
<td><div><div class="class-title"><span class="ipc-text">Architecture, e.g. interconnection topology</span><span class="date-revised"> [2023-01]</span></div></div></td></tr></table>
<table class="classItem subclassgt8" id="G06N3/0409"><tr><td></td><td></td><td></td>
<td class="symbol"><div><span class="symbol"><span class="alink">G06N&nbsp;3/0409</span></span></div></td>
<td width="30" title="Indent level is 3"><div><span class="indent"><b>. . . </b></span></div></td>
<td><div><div class="class-title"><span class="cpc-specific-text"><span class="sbracket">{</span><span class="cpc-text">Adaptive resonance theory [ART] networks</span><span class="sbracket">}</span></span><span class="date-revised"> [2023-01]</span></div></div></td></tr></table>
<table class="classItem subclassgt8" id="G06N3/08"><tr><td></td><td class="note-warning-indicator"></td><td></td>
<td class="symbol"><div><span class="symbol"><span class="alink">G06N&nbsp;3/08</span></span></div></td>
<td width="20" title="Indent level is 2"><div><span class="indent"><b>. . </b></span></div></td>
<td><div><div class="class-title"><span class="ipc-text">Learning methods</span><span class="date-revised"> [2023-01]</span></div><div class="notes-and-warnings"><div class="note">WARNING<p></p></div></div></div></td></tr></table>
<table class="classItem subclassgt8" id="G06N3/082"><tr><td></td><td></td><td></td>
<td class="symbol"><div><span class="symbol"><span class="alink">G06N&nbsp;3/082</span></span></div></td>
<td width="30" title="Indent level is 3"><div><span class="indent"><b>. . . </b></span></div></td>
<td><div><div class="class-title"><span class="ipc-text">modifying the architecture, e.g. adding, deleting or silencing nodes or connections</span><span class="date-revised"> [2023-01]</span></div></div></td></tr></table>
<table class="classItem subclassgt8" id="G06N3/084"><tr><td></td><td></td><td></td>
<td class="symbol"><div><span class="symbol"><span class="alink">G06N&nbsp;3/084</span></span></div></td>
<td width="30" title="Indent level is 3"><div><span class="indent"><b>. . . </b></span></div></td>
<td><div><div class="class-title"><span class="ipc-text">Backpropagation, e.g. using gradient descent</span><span class="date-revised"> [2023-01]</span></div></div></td></tr></table>
<table class="classItem subclassgt8" id="G06N3/0985"><tr><td></td><td></td><td></td>
<td class="symbol"><div><span class="symbol"><span class="alink">G06N&nbsp;3/0985</span></span></div></td>
<td width="30" title="Indent level is 3"><div><span class="indent"><b>. . . </b></span></div></td>
<td><div><div class="class-title"><span class="ipc-text">Hyperparameter optimisation; Meta-learning; Learning-to-learn</span><span class="date-revised"> [2023-01]</span></div></div></td></tr></table>
</div></div>
<table class="classItem subclass8" id="G06N20/00"><tr><td></td><td></td><td></td>
<td class="symbol"><div><span class="symbol"><span class="alink">G06N&nbsp;20/00</span></span></div></td>
<td><div><div class="class-title"><span class="ipc-text">Machine learning</span><span class="date-revised"> [2019-01]</span></div></div></td></tr></table>
</div>
</body></html>
"""
