const puppeteer = require("puppeteer");

async function scrapeGuru() {

    const browser = await puppeteer.launch({ headless: true });
    const page = await browser.newPage();

    await page.goto("https://www.guru.com/d/jobs/", {
        waitUntil: "networkidle2"
    });

    await page.waitForSelector(".jobRecord");

    const jobs = await page.evaluate(() => {

        const jobList = [];
        const rows = document.querySelectorAll(".jobRecord");

        rows.forEach(row => {

            const titleElement = row.querySelector("h2 a");
            const descElement = row.querySelector(".jobDescription");

            const title = titleElement ? titleElement.innerText.trim() : "";
            const description = descElement ? descElement.innerText.trim() : "";
            const link = titleElement ? titleElement.href : "";

            if (title) {
                jobList.push({
                    title: title,
                    company: "Guru",
                    link: link,
                    description: description
                });
            }

        });

        return jobList.slice(0, 10);
    });

    await browser.close();
    return jobs;
}

// ✅ IMPORTANT (safe export)
module.exports = { scrapeGuru };