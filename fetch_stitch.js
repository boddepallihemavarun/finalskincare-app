const fs = require('fs');
const https = require('https');
const path = require('path');

const jsonPath = 'C:/Users/nikhil karthik/.gemini/antigravity/brain/5c9efd32-00bc-4e28-a540-c80950d32ea0/.system_generated/steps/188/output.txt';
const outDir = path.join(__dirname, 'stitch_screens');

if (!fs.existsSync(outDir)) fs.mkdirSync(outDir);

const raw = fs.readFileSync(jsonPath, 'utf8');
const data = JSON.parse(raw);

const targetCoords = [
  '1f0bc47b7234426c8dec4021195450e3', // Advanced Face Scanner
  'ea59eebcc0324c91a321444ebf32f524', // Login Screen
  'cb4d899505ac405690459cb04f27f539', // Luxury Dashboard
  'f00b2055b7494198983a82e719825b9b', // Hero 1
  'e0ca5a0ce145497bb9f0e82a32778765', // Hero 2
  'b7c920725cea494994341c0579d4b315'  // Face Scanner 2
];

const { execSync } = require('child_process');

async function downloadUrl(url, dest) {
  return new Promise((resolve, reject) => {
    try {
      execSync(`curl.exe -s -L "${url}" -o "${dest}"`);
      resolve();
    } catch (e) {
      reject(e);
    }
  });
}

async function run() {
  for (const screen of data.screens) {
    const id = screen.name.split('/').pop();
    if (targetCoords.includes(id) && screen.htmlCode) {
      const title = screen.title.replace(/\s+/g, '_');
      const filename = `${title}_${id}.html`;
      console.log(`Downloading ${filename}...`);
      await downloadUrl(screen.htmlCode.downloadUrl, path.join(outDir, filename));
      console.log(`Saved ${filename}`);
    }
  }
}

run().catch(console.error);
