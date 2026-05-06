const puppeteer = require("puppeteer");

async function scrapeJobs() {

    const browser = await puppeteer.launch({
        headless: false,   // change to true later
        defaultViewport: null
    });

    const page = await browser.newPage();

    // Open RemoteOK jobs page
    await page.goto("https://remoteok.com/remote-dev-jobs", {
        waitUntil: "networkidle2"
    });

    // Wait for jobs table
    await page.waitForSelector("tr.job");

    // STEP 1: Get basic job info (title, company, link)
    const jobs = await page.evaluate(() => {

        const jobList = [];
        const rows = document.querySelectorAll("tr.job");

        rows.forEach(row => {

            const titleElement = row.querySelector("h2");
            const companyElement = row.querySelector("h3");
            const linkElement = row.querySelector("a.preventLink");

            const title = titleElement ? titleElement.innerText.trim() : "";
            const company = companyElement ? companyElement.innerText.trim() : "";
            const link = linkElement
                ? "https://remoteok.com" + linkElement.getAttribute("href")
                : "";

            if (title && link) {
                jobList.push({
                    title: title,
                    company: company,
                    link: link
                });
            }

        });

        return jobList.slice(0, 10); // limit to 10 jobs (important)
    });

    console.log("Basic jobs fetched:", jobs.length);

    // STEP 2: Visit each job page and extract full description
    for (let job of jobs) {

        const jobPage = await browser.newPage();

        try {
            await jobPage.goto(job.link, {
                waitUntil: "networkidle2"
            });

            await jobPage.waitForSelector(".description", { timeout: 5000 });

            const description = await jobPage.evaluate(() => {
                const descElement = document.querySelector(".description");
                return descElement ? descElement.innerText.trim() : "";
            });

            job.description = description || "No description found";

        } catch (error) {
            job.description = "Error fetching description";
        }

        await jobPage.close();
    }

    // STEP 3: Output JSON (important for Python)
    
    
    return jobs;
}

module.exports = scrapeJobs;