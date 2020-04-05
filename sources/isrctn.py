from bs4 import BeautifulSoup
import requests
import utils
from pprint import pprint

SOURCE = "isrctn.com"
FILENAME = "isrctn.json"
BASE_URL = "https://www.isrctn.com"
QUERY_URL = "{BASE_URL}/search?q={query}"
PAGINATE_QUERY = "&page={page_num}&searchType=basic-search"

def clean_empty(d):
    if not isinstance(d, (dict, list)):
        return d
    if isinstance(d, list):
        return [v for v in (clean_empty(v) for v in d) if v]
    return {k: v for k, v in ((k, clean_empty(v)) for k, v in d.items()) if v}


def to_iso8601(date):
    comps = date.split("/")
    if len(comps) == 3:
        return f"{comps[2]}-{comps[1]}-{comps[0]}"
    else:
        return None


def parse_plain_english_summary(summary):
    p1 = "Background and study aims"
    p2 = "Who can participate?"
    p3 = "What does the study involve?"
    p4 = "What are the possible benefits and risks of participating?"
    p5 = "Where is the study run from?"
    p6 = "When is the study starting and how long is it expected to run for?"
    p7 = "Who is funding the study?"
    p8 = "Who is the main contact?"

    summary_data = {}
    try:
        background_study_aims = summary.split(p1)[1].split(p2)[0]
        summary_data["background_study_aims"] = background_study_aims
        who_can_participate = summary.split(p2)[1].split(p3)[0]
        summary_data["who_can_participate"] = who_can_participate
        study_involves = summary.split(p3)[1].split(p4)[0]
        summary_data["study_involves"] = study_involves
        benefits_risks = summary.split(p4)[1].split(p5)[0]
        summary_data["benefits_risks"] = benefits_risks
        where_run_from = summary.split(p5)[1].split(p6)[0]
        summary_data["where_run_from"] = where_run_from
        when_start_how_long = summary.split(p6)[1].split(p7)[0]
        summary_data["when_start_how_long"] = when_start_how_long
        who_funding = summary.split(p7)[1].split(p8)[0]
        summary_data["who_funding"] = who_funding
        main_contact = summary.split(p8)[1]
        summary_data["main_contact"]
    except Exception as e:
        return summary_data

    return summary_data


def find(query):
    data = {}
    count = 0
    url = QUERY_URL.format(BASE_URL=BASE_URL, query=query)
    page = requests.get(url)
    if page.status_code == 200:
        soup = BeautifulSoup(page.content, "html.parser")

        results_number = soup.findAll("span", {"class": "Control_name"})
        if len(results_number) == 0:
            num_pages = 0
        else:
            num_pages = int(results_number[1].text.split("of")[1].strip())

        for page_num in range(num_pages):
            url = QUERY_URL.format(
                BASE_URL=BASE_URL, query=query
            ) + PAGINATE_QUERY.format(page_num=page_num)
            page = requests.get(url)
            if page.status_code == 200:
                soup = BeautifulSoup(page.content, "html.parser")
                my_lis = soup.findAll("li", {"class": "ResultsList_item"})
                for result in my_lis:
                    for link in result.find_all("a", href=True):
                        isrctn_id = link.text.split(":")[0].strip()
                        title = link.text.split(":")[1].strip()
                        link = link.get("href").split("?")[0]
                        if link:
                            url = f"{BASE_URL}{link}"
                            page = requests.get(url)
                            if page.status_code == 200:
                                soup = BeautifulSoup(page.content, "html.parser")
                                dds = soup.findAll("dd", {"class": "Meta_value"})
                                dd_texts = [dd.text.strip() for dd in dds]

                                condition_category = dd_texts[0]
                                date_applied = to_iso8601(dd_texts[1])
                                date_assigned = to_iso8601(dd_texts[2])
                                last_edited = to_iso8601(dd_texts[3])
                                prospective_retrospective = dd_texts[4]
                                overall_trial_status = dd_texts[5]
                                recruitment_status = dd_texts[6]

                                ps = soup.findAll("p")
                                plain_english_summary = ps[0].text
                                summary_data = parse_plain_english_summary(
                                    plain_english_summary
                                )

                                cleaned_ps = [p.text.strip().rstrip() for p in ps[1:]]

                                primary_contact = {
                                    "type": cleaned_ps[1],
                                    "name": cleaned_ps[2],
                                    "orcid_id": cleaned_ps[3],
                                    "contact_details": cleaned_ps[4],
                                }
                                info_section_titles = soup.findAll(
                                    "h3", {"class": "Info_section_title"}
                                )

                                num_additional_contacts = 0
                                for title in info_section_titles:
                                    if "Additional contact" in title.text:
                                        num_additional_contacts += 1

                                additional_contacts = []

                                current_index = 5

                                for i in range(num_additional_contacts):
                                    contact_type = cleaned_ps[current_index]
                                    current_index += 1
                                    name = cleaned_ps[current_index]
                                    current_index += 1
                                    orcid_id = cleaned_ps[current_index]
                                    current_index += 1
                                    contact_details = cleaned_ps[current_index]
                                    current_index += 1
                                    additional_contact = {
                                        "type": contact_type,
                                        "name": name,
                                        "orcid_id": orcid_id,
                                        "contact_details": contact_details,
                                    }
                                    additional_contacts.append(additional_contact)

                                # numbers
                                eudract_number = cleaned_ps[current_index]
                                current_index += 1
                                clinical_trials_gov_number = cleaned_ps[current_index]
                                current_index += 1
                                protocol_serial_number = cleaned_ps[current_index]
                                current_index += 1

                                # study information
                                scientific_title = cleaned_ps[current_index]
                                current_index += 1
                                acronym = cleaned_ps[current_index]
                                current_index += 1
                                study_hypothesis = cleaned_ps[current_index]
                                current_index += 1
                                ethics_approval = cleaned_ps[current_index]
                                current_index += 1
                                study_design = cleaned_ps[current_index]
                                current_index += 1
                                primary_study_design = cleaned_ps[current_index]
                                current_index += 1
                                secondary_study_design = cleaned_ps[current_index]
                                current_index += 1
                                trial_setting = cleaned_ps[current_index]
                                current_index += 1
                                trial_type = cleaned_ps[current_index]
                                current_index += 1
                                patient_information_sheet = cleaned_ps[current_index]
                                current_index += 1
                                condition = cleaned_ps[current_index]
                                current_index += 1
                                intervention = cleaned_ps[current_index]
                                current_index += 1
                                intervention_type = cleaned_ps[current_index]
                                current_index += 1
                                phase = cleaned_ps[current_index]
                                current_index += 1
                                drug_names = cleaned_ps[current_index]
                                current_index += 1
                                primary_outcome_measure = cleaned_ps[current_index]
                                current_index += 1
                                secondary_outcome_measure = cleaned_ps[current_index]
                                current_index += 1
                                overall_trial_start_date = to_iso8601(
                                    cleaned_ps[current_index]
                                )
                                current_index += 1
                                overall_trial_end_date = to_iso8601(
                                    cleaned_ps[current_index]
                                )
                                current_index += 1
                                reason_abandoned = cleaned_ps[current_index]
                                if reason_abandoned == "":
                                    reason_abandoned = None
                                current_index += 1

                                # eligibility
                                participant_inclusion_criteria = cleaned_ps[
                                    current_index
                                ]
                                current_index += 1
                                participant_type = cleaned_ps[current_index]
                                current_index += 1
                                age_group = cleaned_ps[current_index]
                                current_index += 1
                                gender = cleaned_ps[current_index]
                                current_index += 1
                                target_num_participants = cleaned_ps[current_index]
                                current_index += 1

                                has_total_final_enrolment = False
                                # at least one has Total final enrolment
                                # ignore this because it is not common
                                for title in info_section_titles:
                                    if "Total final enrolment" in title.text:
                                        current_index += 1

                                participant_exclusion_criteria = cleaned_ps[
                                    current_index
                                ]
                                current_index += 1
                                recruitment_start_date = to_iso8601(
                                    cleaned_ps[current_index]
                                )
                                current_index += 1
                                recruitment_end_date = to_iso8601(
                                    cleaned_ps[current_index]
                                )
                                current_index += 1

                                # locations
                                countries_of_recruitment = cleaned_ps[current_index]
                                current_index += 1

                                num_trial_participating_centers = 0
                                for title in info_section_titles:
                                    if "Trial participating centre" in title.text:
                                        num_trial_participating_centers += 1

                                trial_participation_centers = []

                                for i in range(num_trial_participating_centers):
                                    trial_participation_center = {
                                        "info": cleaned_ps[current_index]
                                        .strip()
                                        .rstrip()
                                    }
                                    current_index += 1
                                    trial_participation_centers.append(
                                        trial_participation_center
                                    )

                                # sponsor information
                                organization = cleaned_ps[current_index]
                                current_index += 1
                                sponsor_details = cleaned_ps[current_index]
                                current_index += 1
                                sponsor_type = cleaned_ps[current_index]
                                current_index += 1
                                sponsor_website = cleaned_ps[current_index]
                                current_index += 1

                                # funders
                                funder_type = cleaned_ps[current_index]
                                current_index += 1
                                funder_name = cleaned_ps[current_index]
                                current_index += 1
                                alternative_name = cleaned_ps[current_index]
                                current_index += 1
                                funding_body_type = cleaned_ps[current_index]
                                current_index += 1
                                funding_body_subtype = cleaned_ps[current_index]
                                current_index += 1
                                location = cleaned_ps[current_index]
                                current_index += 1

                                # results and publications
                                publication_dissemination_plan = cleaned_ps[
                                    current_index
                                ]
                                current_index += 1
                                intention_to_public_date = cleaned_ps[current_index]
                                intention_to_public_date = to_iso8601(
                                        intention_to_public_date
                                )
                                current_index += 1
                                participant_level_data = cleaned_ps[current_index]
                                current_index += 1
                                basic_results = cleaned_ps[current_index]
                                current_index += 1
                                publication_list = cleaned_ps[current_index]
                                current_index += 1
                                publication_citations = cleaned_ps[current_index]
                                current_index += 1


                                primary_contact_list = [x.strip() for x in primary_contact["contact_details"].split("\n")]

                                institution = primary_contact_list[0].strip()
                                phone = primary_contact_list[2].strip()
                                email = primary_contact_list[3].strip()

                                contact_information = {
                                        "name": primary_contact["name"],
                                        "phone": phone,
                                        "email": email,
                                        }

                                this_entry = {
                                    # Meta keys
                                    #"id": isrctn_id,
                                    "_source": SOURCE,

                                    # Essential keys
                                    "title": title.text,
                                    "url": url,
                                    "timestamp": last_edited,
                                    "sample_size": target_num_participants,
                                    "recruiting_status": recruitment_status,
                                    "gender": gender,
                                    "target_disease": condition,
                                    "intervention": drug_names,
                                    "sponsor": organization,
                                    "summary": plain_english_summary,
                                    "contact_information": contact_information,
                                    "institution": institution,
                                    # There is logic at the bottom to fix this if needed
                                    "abandoned": True,
                                    "reason_abandoned": reason_abandoned,

                                    # cut (for now)
                                    # "age_group": age_group,

                                    # ISRCTN specific keys
                                    "condition_category": condition_category,
                                    "date_applied": date_applied,
                                    "date_assigned": date_assigned,
                                    "last_edited": last_edited,
                                    "prospective_retrospective": prospective_retrospective,
                                    "overall_trial_status": overall_trial_status,
                                    "summary": summary_data,
                                    "primary_contact": primary_contact,
                                    #"additional_contacts": additional_contacts,
                                    "numbers": {
                                        "eudract_number": eudract_number,
                                        "clinical_trials_gov_number": clinical_trials_gov_number,
                                        "protocol_serial_number": protocol_serial_number,
                                    },
                                    "study_information": {
                                        "scientific_title": scientific_title,
                                        "acronym": acronym,
                                        "study_hypothesis": study_hypothesis,
                                        "ethics_approval": ethics_approval,
                                        "study_design": study_design,
                                        "primary_study_design": primary_study_design,
                                        "secondary_study_design": secondary_study_design,
                                        "trial_setting": trial_setting,
                                        "trial_type": trial_type,
                                        "patient_information_sheet": patient_information_sheet,
                                        "condition": condition,
                                        "intervention": intervention,
                                        "intervention_type": intervention_type,
                                        "phase": phase,
                                        "drug_names": drug_names,
                                        "primary_outcome_measure": primary_outcome_measure,
                                        "secondary_outcome_measure": secondary_outcome_measure,
                                        "overall_trial_start_date": overall_trial_start_date,
                                        "overall_trial_end_date": overall_trial_end_date,
                                        "reason_abandoned": reason_abandoned,
                                    },
                                    "elibibility": {
                                        "participant_inclusion_criteria": participant_inclusion_criteria,
                                        "participant_type": participant_type,
                                        "age_group": age_group,
                                        "gender": gender,
                                        "target_num_participants": target_num_participants,
                                        "participant_exclusion_criteria": participant_exclusion_criteria,
                                        "recruitment_start_date": recruitment_start_date,
                                        "recruitment_end_date": recruitment_end_date,
                                    },
                                    "locations": {
                                        "countries_of_recruitment": countries_of_recruitment,
                                        #"trial_participation_centers": trial_participation_centers,
                                    },
                                    "sponsor_info": {
                                        "organization": organization,
                                        "sponsor_details": sponsor_details,
                                        "sponsor_type": sponsor_type,
                                        "sponsor_website": sponsor_website,
                                    },
                                    "funder": {
                                        "funder_type": funder_type,
                                        "funder_name": funder_name,
                                        "alternative_name": alternative_name,
                                        "funding_body_type": funding_body_type,
                                        "funding_body_subtype": funding_body_subtype,
                                        "location": location,
                                    },
                                    "results_and_publications": {
                                        "publication_dissemination_plan": publication_dissemination_plan,
                                        "intention_to_public_date": intention_to_public_date,
                                        "participant_level_data": participant_level_data,
                                        "basic_results": basic_results,
                                        "publication_list": publication_list,
                                        "publication_citations": publication_citations,
                                    },
                                }

                                if reason_abandoned == None:
                                    del this_entry["reason_abandoned"]
                                    this_entry["abandoned"] = False

                                print(this_entry)
                                print("***")

                                this_entry = clean_empty(this_entry)
                                data[url] = this_entry
                                count += 1

    print(f"Fetched {count} results for {query}")
    return data


def translate(info):
    return info
