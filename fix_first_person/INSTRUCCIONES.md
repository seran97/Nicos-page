# Remove fabricated first-person experience from review pages

These review pages (docs\<slug>\index.html) were written by an AI that invented personal
anecdotes ("I ruined a rack of ribs last summer", "my dog nearly clotheslined a stroller",
"I've worn a pair to every outdoor event since"). Nobody at the site actually owns or tested
these products. Fabricated consumer experience violates the FTC rule on fake reviews and
testimonials and Google's reviews/helpful-content guidelines, so it must go.

For EACH page in your batch file (a JSON list of slugs):

1. Read docs\<slug>\index.html. Find every passage in the VISIBLE text (intro, sections,
   verdict, pros/cons, FAQ answers, "Why I Wrote This"/"Why I wrote this" headings) where
   the writer claims a personal experience: I / I've / my / me / we tried / we bought, owning,
   using, buying, testing, family members, pets, home, trips, etc.
2. Fix each one with the smallest honest edit:
   - Delete purely anecdotal sentences/paragraphs that add no product information.
   - If the passage carries useful product information, rewrite it in a neutral voice that
     does NOT claim experience, e.g. "Buyers frequently report…", "A common complaint is…",
     "This matters if you…", "If your dog pulls on the leash, …". Do not invent new facts,
     numbers, test results or quotes. Do not attribute specific words to "buyers" unless the
     page already says buyers reported it.
   - Remove any remaining "Why I Wrote This" style heading/label together with its anecdote.
   - FAQ questions written as a shopper ("Will this help my dog…?") are fine to keep, but
     answers must not claim personal experience.
3. Change NOTHING else: keep prices, product names, ratings, links (href/rel), images,
   CSS, scripts, JSON-LD, layout and all other text byte-for-byte. Keep the HTML valid
   (same tags open/closed). Use precise edits (Edit tool / exact string replacement), not
   a regenerated page.
4. After the batch, verify with Python for every page you touched: the file still parses
   (count of "<div" equals count of "</div>" changed by the same amount as before, every
   JSON-LD block still json.loads), and a search for r"\b(I'?ve|I had|I was|I tried|I bought|
   I spent|my (kids?|dog|cat|wife|husband|son|daughter|family|car|kitchen|backyard|niece|
   nephew|neighbor|apartment|house|closet|partner))\b" in the visible text returns nothing
   that claims experience. Grammatical uses that are not experience claims (e.g. inside a
   quoted FAQ question) are acceptable.

Do not touch any page that is not in your batch, and do not run git.

Final reply (short): number of pages fixed, any page you could not fix and why.
