// Saves every page of a chapter from a web reader that draws its pages on <canvas> elements (not <img>), as one zip of page-001.webp, page-002.webp, ...
// Used for the Japanese Shachou to Sake to Hoshi ch. 3 test pages (spec 01), from Niconico's reader: https://sp.manga.nicovideo.jp/watch/mg939870
//
// How to use (Chrome or Edge):
// 1. Open the chapter and switch the reader to vertical (infinite) scrolling if it has that option.
// 2. Open the console (View > Developer > JavaScript Console), paste this whole file and press Enter.
// 3. Leave the tab in front while it scrolls to the end. The zip downloads by itself when it's done.
// 4. Unzip it into ~/Documents/Panelyze/<spec folder>/test-raws/<chapter>/ (for Shachou ch. 3: test-raws/shachou-ch3-ja/).

(async function saveCanvasPagesAsZip() {
  const zipName = 'shachou-ch3-ja.zip';
  const scrollStep = 0.7; // Share of the screen scrolled each time, so no page is skipped.
  const waitMs = 700; // Time for the pages that just came into view to be drawn.

  // The element that scrolls: the window, or the reader's own box.
  function getScrollContainer() {
    let best = document.scrollingElement || document.documentElement;
    let mostScroll = best.scrollHeight - best.clientHeight;
    for (const element of document.querySelectorAll('div, main, section')) {
      const scrolls = /(auto|scroll)/.test(getComputedStyle(element).overflowY);
      const extra = element.scrollHeight - element.clientHeight;
      if (scrolls && extra > mostScroll) {
        mostScroll = extra;
        best = element;
      }
    }
    return best;
  }

  const scroller = getScrollContainer();
  const isWindow = scroller === document.documentElement || scroller === document.body;
  const getTop = () => (isWindow ? window.scrollY : scroller.scrollTop);
  const getViewHeight = () => (isWindow ? window.innerHeight : scroller.clientHeight);
  const scrollTo = (y) => (isWindow ? window.scrollTo(0, y) : (scroller.scrollTop = y));
  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

  const saved = new WeakSet();
  const files = [];
  scrollTo(0);
  await sleep(800);
  console.log('Scrolling through the chapter and saving each page as it is drawn...');

  for (let stuck = 0; stuck < 2; ) {
    let canvases = document.querySelectorAll('canvas.max-h-full.max-w-full');
    if (canvases.length === 0) canvases = document.querySelectorAll('canvas');
    for (const canvas of canvases) {
      // Already saved, or not drawn yet.
      if (saved.has(canvas) || canvas.width === 0 || canvas.height === 0) continue;
      let blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/webp', 0.9));
      let extension = 'webp';
      if (!blob) {
        blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/png'));
        extension = 'png';
      }
      // A blank canvas that hasn't been painted yet is tiny.
      if (!blob || blob.size < 2000) continue;
      saved.add(canvas);
      const name = `page-${String(files.length + 1).padStart(3, '0')}.${extension}`;
      files.push({ name, bytes: new Uint8Array(await blob.arrayBuffer()) });
      console.log(`Saved ${name}`);
    }

    // At the bottom twice in a row: done.
    const atBottom = getTop() >= scroller.scrollHeight - getViewHeight() - 5;
    stuck = atBottom ? stuck + 1 : 0;
    scrollTo(getTop() + getViewHeight() * scrollStep);
    await sleep(waitMs);
  }

  if (files.length === 0) {
    console.error('No pages found. Is the chapter open, and are its pages drawn on <canvas> elements?');
    return;
  }
  const link = document.createElement('a');
  link.href = URL.createObjectURL(new Blob([makeZip(files)], { type: 'application/zip' }));
  link.download = zipName;
  link.click();
  console.log(`Done: ${files.length} pages in ${zipName}.`);
})();

// A zip with the files stored as they are (images are compressed already), so no library is needed.
function makeZip(files) {
  const crcTable = Array.from({ length: 256 }, (_, n) => {
    let c = n;
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    return c >>> 0;
  });
  const crc32 = (bytes) => {
    let crc = 0xffffffff;
    for (const byte of bytes) crc = crcTable[(crc ^ byte) & 0xff] ^ (crc >>> 8);
    return (crc ^ 0xffffffff) >>> 0;
  };
  const now = new Date();
  const dosTime = (now.getHours() << 11) | (now.getMinutes() << 5) | (now.getSeconds() >> 1);
  const dosDate = ((now.getFullYear() - 1980) << 9) | ((now.getMonth() + 1) << 5) | now.getDate();
  const encoder = new TextEncoder();
  const parts = [];
  const directory = [];
  let offset = 0;

  for (const file of files) {
    const name = encoder.encode(file.name);
    const crc = crc32(file.bytes);
    const header = new DataView(new ArrayBuffer(30));
    header.setUint32(0, 0x04034b50, true); // Local file header
    header.setUint16(4, 20, true); // Version needed
    header.setUint16(10, dosTime, true);
    header.setUint16(12, dosDate, true);
    header.setUint32(14, crc, true);
    header.setUint32(18, file.bytes.length, true); // Size stored
    header.setUint32(22, file.bytes.length, true); // Size
    header.setUint16(26, name.length, true);
    parts.push(new Uint8Array(header.buffer), name, file.bytes);

    const entry = new DataView(new ArrayBuffer(46));
    entry.setUint32(0, 0x02014b50, true); // Central directory entry
    entry.setUint16(4, 20, true); // Version made by
    entry.setUint16(6, 20, true); // Version needed
    entry.setUint16(12, dosTime, true);
    entry.setUint16(14, dosDate, true);
    entry.setUint32(16, crc, true);
    entry.setUint32(20, file.bytes.length, true);
    entry.setUint32(24, file.bytes.length, true);
    entry.setUint16(28, name.length, true);
    entry.setUint32(42, offset, true); // Where its local header starts
    directory.push(new Uint8Array(entry.buffer), name);
    offset += 30 + name.length + file.bytes.length;
  }

  const directorySize = directory.reduce((total, part) => total + part.length, 0);
  const end = new DataView(new ArrayBuffer(22));
  end.setUint32(0, 0x06054b50, true); // End of central directory
  end.setUint16(8, files.length, true);
  end.setUint16(10, files.length, true);
  end.setUint32(12, directorySize, true);
  end.setUint32(16, offset, true);
  return new Blob([...parts, ...directory, new Uint8Array(end.buffer)]);
}
