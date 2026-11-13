# Publishing to the Chrome Web Store

**Summary.** Run `scripts/package.sh` to build `dist/simple-spelling-<version>.zip`,
upload it in the Chrome Web Store developer dashboard, and fill in the
listing and privacy forms with the text below. You need a Chrome Web Store
developer account (a one-time US$5 registration fee). Review usually takes
a few days. Because the extension runs on every site, expect a closer review
of the host permission.

## 1. Build the upload

```bash
python3 tools/make_icons.py      # only if the icon design changes
scripts/package.sh               # -> dist/simple-spelling-0.1.0.zip
```

For each new release, bump `version` in `extension/manifest.json` first. The
store rejects a version it has already seen.

## 2. Create the item

1. Go to the [developer dashboard](https://chrome.google.com/webstore/devconsole)
   and register if you haven't.
2. Click **New item** and upload the zip.

## 3. Store listing

- **Name:** Simple Spelling
- **Summary:** taken from the manifest's `description`:
  "Read the web in simpler, more phonetic English spelling: tho, thru, nite,
  luv, hed, skool. One switch turns it on or off."
- **Category:** Accessibility
- **Language:** English
- **Icon:** `extension/icons/icon128.png`
- **Screenshots:** at least one, 1280×800 or 640×400. Suggestion: the same
  article before and after switching on, with the popup open.
- **Description:**

> English spelling is famously irregular. *Though, through, tough, cough* all
> end in *-ough* and none of them rhyme. Simple Spelling rewrites the pages you
> read using simpler, more consistent spellings, mostly the casual ones people
> already use:
>
> *I thawt we shud go out tonite, but my frend sed she wos too tired. She has
> sum munney, tho, and we hav enuff to buy a fone.*
>
> - **One switch.** Turn it on and every page is respelled; turn it off and
>   the original text comes back.
> - **Only fixes what's actually odd.** A spelling changes only if it's
>   irregular in both American and British English. The rules are listed in
>   the popup, most confusing first: *ough*, silent letters, *ea* in *head*,
>   *o* in *love*, *igh*, *ph*, and more.
> - **Stays readable.** It never turns a word into a different word, leaves
>   names alone, and doesn't touch code or text boxes.
> - **Private.** Everything happens in your browser. No data is collected or
>   sent anywhere.
>
> The rules, and how they were chosen, are documented at
> https://github.com/robennals/simple-spelling-chrome

## 4. Privacy practices tab

- **Single purpose:** "Displays the text of web pages in a simplified,
  more phonetic English spelling."
- **Permission justification, `storage`:** "Remembers whether the user has
  switched respelling on or off."
- **Host permission justification (content script on all URLs):** "The
  extension respells the text of whatever page the user is reading, so it
  has to run on any site. It only changes how text is displayed and sends
  nothing anywhere."
- **Remote code:** No. All code and data are in the package.
- **Data usage:** tick nothing; the extension collects no user data. Certify
  the three disclosures.
- **Privacy policy URL:**
  https://github.com/robennals/simple-spelling-chrome/blob/main/docs/privacy.md

## 5. Submit

Choose **Public** visibility and submit for review.
