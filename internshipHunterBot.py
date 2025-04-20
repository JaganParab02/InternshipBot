from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time

# -------- AI Modules --------
from sentence_transformers import SentenceTransformer, util
import fitz  # <-- fixed after cleaning and reinstalling PyMuPDF




# -------- Job Scraper --------
def scrape_jobs(email, password, keywords, location="Remote", max_jobs=30):
    jobNum = 1
    options = Options()
    # options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")   
    options.add_argument("--start-maximized")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    wait = WebDriverWait(driver, 10)
    driver.get("https://www.linkedin.com/login")

    # Login
    driver.find_element(By.ID, "username").send_keys(email)
    driver.find_element(By.ID, "password").send_keys(password)
    driver.find_element(By.XPATH, "//button[@type='submit']").click()

    # Go to Jobs page with filters
    driver.get(f"https://www.linkedin.com/jobs/search/?keywords={keywords}&location={location}&f_AL=true")
    time.sleep(2)

    job_list = []
    visited_job_ids = set()

    while len(job_list) < max_jobs:
        jobs = driver.find_elements(By.CSS_SELECTOR, "div.scaffold-layout__list-detail-container div.scaffold-layout__list-detail-inner div.scaffold-layout__list div ul li.scaffold-layout__list-item")

        for job in jobs:
            try:
                 
                if (jobNum != 0 and jobNum % 25) == 0:
                    wait.until(EC.presence_of_element_located((By.XPATH, "//button#ember274")))
                    wait.until(EC.element_to_be_clickable((By.XPATH, "//button#ember274")))
                    nextButton = driver.find_element(By.XPATH, "//button#ember274")
                    nextButton.click()
                    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.scaffold-layout__list-detail-container div.scaffold-layout__list-detail-inner div.scaffold-layout__list div ul li.scaffold-layout__list-item")))
                jobNum += 1
                
                job.click()
                time.sleep(2)
                desc_divs = driver.find_elements(By.CSS_SELECTOR, "div.jobs-details__main-content--single-pane article.jobs-description__container div.jobs-description-content div#job-details")

                if desc_divs:
                    desc_div = desc_divs[0]  # Grab the first matching element

                # Get all <span> elements under <p dir="ltr">
                spans = desc_div.find_elements(By.CSS_SELECTOR, 'div.mt4 p[dir="ltr"] span')

                # Extract and join the text
                job_info_string = "\n".join([span.text.strip() for span in spans if span.text.strip()])                
                job_url = driver.current_url
                job_id = job_url.split("currentJobId=")[-1].split("&")[0]
                if job_id in visited_job_ids:
                    continue
                visited_job_ids.add(job_id)

                # Scope your find_element to the right-side job detail container
                # job_detail_container = wait.until(
                #     EC.presence_of_element_located((By.CLASS_NAME, "jobs-search__job-details--container"))
                # )
                title_elem = job.find_element(By.CSS_SELECTOR, ".artdeco-entity-lockup__title a")
                company_elem = job.find_element(By.CSS_SELECTOR, ".artdeco-entity-lockup__subtitle span")
                location_elem = job.find_element(By.CSS_SELECTOR, ".artdeco-entity-lockup__caption ul.job-card-container__metadata-wrapper li span[dir='ltr']")

                easy_apply = False
                try:
                    apply_button = driver.find_element(By.CLASS_NAME, "jobs-apply-button")
                    if "Easy Apply" in apply_button.text:
                        easy_apply = True
                except:
                    pass

                if easy_apply:
                    job_data = {
                        "title": title_elem.text,
                        "company": company_elem.text,
                        "location": location_elem.text,
                        "job_id": job_id,
                        "url": job_url,
                        "job_context": job_info_string,
                    }
                    print("Easy Apply Job:", job_data)
                    job_list.append(job_data)

                if len(job_list) >= max_jobs:
                    break
            except Exception as e:
                print("Error parsing job:", e)

        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.END)
        time.sleep(2)

    driver.quit()
    return job_list


# -------- Resume Extractor --------
def extract_resume_text_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()
    return text.strip()


# -------- AI Job Ranking --------
model = SentenceTransformer('all-MiniLM-L6-v2')


def rank_jobs_by_resume_similarity_from_pdf(pdf_path, job_list):
    resume_text = extract_resume_text_from_pdf(pdf_path)
    resume_embedding = model.encode(resume_text, convert_to_tensor=True)

    for job in job_list:
        job_text = f"{job['title']} at {job['company']}, {job['location']}, {job['job_context']}"
        # job_text = f"{job['title']} at {job['company']}, {job['location']}"
        job['score'] = util.cos_sim(resume_embedding, model.encode(job_text, convert_to_tensor=True)).item()

    ranked_jobs = sorted(job_list, key=lambda x: x['score'], reverse=True)
    return ranked_jobs
    
