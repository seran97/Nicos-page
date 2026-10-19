# Parte 3 — Enriquecer páginas delgadas

Project folder: C:\Users\sergi\OneDrive - Revaliu\Escritorio\Trabajo Flash\radar_nichos
Pages: docs\<slug>\index.html (English review / comparison pages, ~350–450 words of real text).
State file: revision\parte3_estado.json — your batch is the list named in your task ("lote_A" or "lote_B").

For EACH page in your batch, one at a time:

1. Read the page. Understand the product type and what the page already says.
2. Add ONE new section, 200–300 words, placed right before the FAQ section (or before the final
   CTA band / footer if there is no FAQ). Heading: "What to Check Before You Buy" (for comparison
   pages: "How to Decide Between Them"). Reuse the page's existing section markup/classes so it
   looks native (copy the structure of a neighbouring <section>/<h2>/<p>).
3. Content rules (Google helpful-content + FTC):
   - Practical, specific buying criteria for THIS product type (specs that matter, what they
     mean, trade-offs, who should skip it). Neutral expert voice.
   - NO first-person experience (no I / my / we tried / we tested), no anecdotes.
   - Do NOT invent numbers, test results, quotes or buyer statistics. Only well-established
     general facts (units, standards) you are sure of; otherwise explain the principle.
   - NO new affiliate links, no prices, no brand promotion.
   - If one of the site's free guides is relevant, add ONE internal link to it inside the text,
     as <a href="/<guide-slug>/">descriptive anchor</a>. Guide slugs and titles are in
     info_content_manifest.json (63 guides; e.g. tent-waterproof-rating-hydrostatic-head-explained,
     how-to-hang-a-camping-hammock-safely, jump-starter-peak-amps-vs-cranking-amps,
     dash-cam-parking-mode-hardwiring-guide, car-vacuum-suction-pa-vs-air-watts,
     do-bug-zappers-kill-mosquitoes, how-to-wash-linen-without-shrinking, ...). Only link a guide
     that exists in that manifest AND as a folder in docs\.
4. Change nothing else on the page (prices, links, JSON-LD, CSS, other text). Keep HTML valid.
5. Verify with Python: <div>/</div> and <section>/</section> counts change by the same amount,
   every JSON-LD block still json.loads, the new section has 200–300 words, no first-person.
6. IMMEDIATELY after each page passes, append its slug to "hechas" in revision\parte3_estado.json
   (read-modify-write the JSON). This is the checkpoint: if the session stops, the next one
   skips pages already in "hechas".

Skip any page already listed in "hechas". Do not touch pages outside your batch. Do not run git.
Final reply (short): pages done, guide links added, anything skipped and why.
