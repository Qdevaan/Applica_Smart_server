const fs = require("fs");
const scrapeRemoteOK = require("./scraper");   // your existing working scraper
const scrapeFreelancer = require("./freelancer");
const { scrapeGuru } = require("./guru");   // ✅ important change

async function main() {

    let allJobs = [];

    try {

        console.log("Fetching RemoteOK...");
        const remoteJobs = await scrapeRemoteOK();

        console.log("Fetching Freelancer...");
        const freelancerJobs = await scrapeFreelancer();

        console.log("Fetching Guru...");
        const guruJobs = await scrapeGuru();

        allJobs = [
            ...remoteJobs,
            ...freelancerJobs,
            ...guruJobs
        ];

    } catch (error) {
        console.error("Error:", error);
    }

    fs.writeFileSync("jobs.json", JSON.stringify(allJobs, null, 2));
    console.log("✅ Jobs saved to jobs.json");
}

main();