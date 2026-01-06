import sys
sys.path.insert(0, 'preprocess')
from sentence_splitter import SentenceSplitter
from semantic_blocker import SemanticChunker, ChunkerConfig, OllamaBackend

text = """Mikel Arteta's Arsenal side marched on to the EFL Cup semi-finals but did it the hard way by winning 8-7 on penalties against Crystal Palace, with Kepa Arrizabalaga saving the 16th spot-kick taken by Maxence Lacroix after 15 successful conversions. Two late goals had resulted in a 1-1 draw after 90 minutes and a lengthy period of stoppage time. The Gunners will now face rivals Chelsea to fight for a place in the final at Wembley, with the first leg of their semi-final set for Stamford Bridge on 14 January.

After bossing much of the quarter-final against Palace and creating the majority of big chances, Arteta's men finally found their breakthrough, which came from a corner in the 80th minute. A well-placed delivery into the box from Bukayo Saka found the head of Riccardo Calafiori and eventually went into the net off Palace centre-back Lacroix. The unfortunate own goal did not dampen Palace's spirits as they went in search of an equaliser. When it finally did arrive, they had club captain Marc Guehi to thank. The England international was the first to react to a knock-on from Jefferson Lerma in the fifth minute of stoppage time.

A fascinating penalty shoot-out then ensued, with both sides delivering spectacular finishes to take the score to 8-7. When the own-goal scorer Lacroix stepped up to take his kick, Arsenal keeper Kepa read its direction and made the save to ensure the Gunners remain on course for their first Wembley appearance in five years.

This was Arsenal's second-highest scoring penalty shootout, after their 9-8 victory against Rotherham in 2003/04. Overall, the Gunners have converted 47 of their last 51 spot-kicks in shoot-outs, giving them a supreme 92 per cent conversion rate.

Arteta told Sky Sports after the game: "I'm very happy to be in the semi-finals. We played against a team who are hard to generate chances against. We generated a lot and we should have scored many more goals." The Arsenal boss had made eight changes to his starting line-up and admitted: "It's always tough because they don't have the right chemistry when they haven't played together. But their attitude is excellent. "I think we had some big individual performances tonight. It's great for Gabriel Jesus tonight, after almost a year out, to start a game and make his 100th [Arsenal] appearance. The commitment within the group is incredible and I'm very happy for the boys."
"""

splitter = SentenceSplitter()
sentences = splitter.split(text)

backend = OllamaBackend(model="llama3:latest", temperature=0.3)
# Try fixed window with 3 sentences
chunker = SemanticChunker(backend, ChunkerConfig(window_size=3))
chunks = chunker.chunk(sentences)

print(f"Total: {len(sentences)} sentences → {len(chunks)} chunks\n")
stats = chunker.get_stats()
print(f"Decisions: {stats['same_unit_count']} SAME, {stats['new_unit_count']} NEW")
print(f"\nDetailed chunks:")
for i, chunk in enumerate(chunks, 1):
    print(f"\n[Chunk {i}] {len(chunk)} sentences:")
    for j, sent in enumerate(chunk, 1):
        preview = sent[:80] + "..." if len(sent) > 80 else sent
        print(f"  {j}. {preview}")
