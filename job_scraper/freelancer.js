const puppeteer = require("puppeteer");

async function scrapeFreelancer() {

    const browser = await puppeteer.launch({ headless: true });
    const page = await browser.newPage();

    await page.goto("https://www.freelancer.com/jobs/software-development/", {
        waitUntil: "networkidle2"
    });

    await page.waitForSelector(".JobSearchCard-item");

    const jobs = await page.evaluate(() => {

        const jobList = [];
        const rows = document.querySelectorAll(".JobSearchCard-item");

        rows.forEach(row => {

            const titleElement = row.querySelector("a.JobSearchCard-primary-heading-link");
            const descElement = row.querySelector(".JobSearchCard-primary-description");

            const title = titleElement ? titleElement.innerText.trim() : "";
            const description = descElement ? descElement.innerText.trim() : "";
            const link = titleElement ? titleElement.href : "";

            if (title) {
                jobList.push({
                    title: title,
                    company: "Freelancer",
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

module.exports = scrapeFreelancer;