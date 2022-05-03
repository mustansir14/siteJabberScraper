import argparse, sys, json, os

def oxfordcomma(listed):
    if len(listed) == 0:
        return ''
    if len(listed) == 1:
        return listed[0]
    if len(listed) == 2:
        return listed[0] + ' and ' + listed[1]
    return ', '.join(listed[:-1]) + ', and ' + listed[-1]

def generate_article(company):

    article = {"title": f"{company['name']} Company Information: Contact, Address, Founders, CEO, Services, and Products"}
    article["description"] = ""
    if "industry" in company:
        article["description"] += f"{company['name']} is a {oxfordcomma(company['industry'])} company"
    else:
        article["description"] += f"{company['name']} is a technology company"
    if "country" in company:
        article["description"] += f" from {company['country']}"
    article["description"] += ". "
    if "type" in company and "isin" in company:
        article["description"] += f"{company['name']} is a {company['type']} company with {company['isin']} ISIN number. "
    elif "type" in company:
        article["description"] += f"{company['name']} is a {company['type']} company. "
    elif "isin" in company:
        article["description"] += f"{company['name']} has {company['isin']} ISIN number"
    if "official_name" in company:
        article["description"] += f"{company['name']}'s official name is {company['official_name']}. "
    if "former_names" in company:
        article["description"] += f"{company['name']} former names are {oxfordcomma(company['former_names'])}. "
    if "traded_as" in company and "industry" in company:
        article["description"] += f"{company['name']} is listed within {oxfordcomma(company['traded_as'])} as a {company['industry'][0]}. "
    elif "traded_as" in company:
        article["description"] += f"{company['name']} is listed within {oxfordcomma(company['traded_as'])}. "
    if "product_types" in company:
        article["description"] += f"{company['name']} produces mainly {oxfordcomma(company['product_types'][:7])}. "
    if "revenue" in company:
        article["description"] += f"{company['name']} has annual revenue of {company['revenue']}. "
    if "net_income" in company and "number_of_employees" in company:
        article["description"] += f"Company net income is {company['net_income']} and it has {company['number_of_employees']} employees."
    elif "net_income" in company:
        article["description"] += f"Company net income is {company['net_income']}."
    elif "number_of_employees" in company:
        article["description"] += f"{company['name']} has {company['number_of_employees']} employees."
    article["description"] += "\n\n"
    article["description"] += f"In this {company['name']} overview the general profile of {company['name']} along with reviews about its products, and complaints about its services along with customer support and contact information will be processed."
    article["questions"] = []
    question_num = 1
    if "founders" in company or "key_people" in company:
        article["questions"].append({"question": f"Question {question_num}: Who is the owner of {company['name']}?"})
        article["questions"][-1]["answer"] = ""
        if "founders" in company:
            article["questions"][-1]["answer"] += f"The owners of {company['name']} are {oxfordcomma(company['founders'])}. "
        if "key_people" in company:
            article["questions"][-1]["answer"] += f"The key people of {company['name']} are {oxfordcomma(company['key_people'])}. "
        question_num += 1
    if "foundation_date" in company:
        article["questions"].append({"question": f"Question {question_num}: When is {company['name']} founded?"})
        article["questions"][-1]["answer"] = f"{company['name']} is founded on {company['foundation_date']}"
        if "founders" in company:
            article["questions"][-1]["answer"] += f",  by {oxfordcomma(company['founders'])}"
        if "country" in company:
            article["questions"][-1]["answer"] += f" in the {company['country']}"
        article["questions"][-1]["answer"] += "."
        if "headquarters" in company:
            article["questions"][-1]["answer"] += f" {company['name']} has headquarters located in {company['country']}."
        question_num += 1
    if "industry" in company:
        article["questions"].append({"question": f"Question {question_num}: What is the industry of {company['name']}?"})
        article["questions"][-1]["answer"] = f"The industries of {company['name']} are {oxfordcomma(company['industry'])}. {company['name']} industries contains {len(company['industry'])} companies."
        if "foundation_date" in company:
            article["questions"][-1]["answer"] += f" {company['name']} is in the {company['industry'][0]} since {company['foundation_date'].split()[-1].strip('(),.')}."
        question_num += 1
    article["questions"].append({"question":  f"Question {question_num}: What are the services of {company['name']}?"})
    if "services" in company:
        article["questions"][-1]["answer"] = f"The services of {company['name']} are {oxfordcomma(company['services'])}. "
    else:
        article["questions"][-1]["answer"] = f"{company['name']} provides high-tech solutions and services. "
    if "industry" in company:
        article["questions"][-1]["answer"] += f"The services of {company['name']} shows the capacity of {company['name']} for providing services for its place in {oxfordcomma(company['industry'][:3])}. "
    if "service_area" in company:
        article["questions"][-1]["answer"] += f"{company['name']}'s service area is {company['service_area']}."
    question_num += 1
    if "headquarters" in company or "official_website" in company:
        article["questions"].append({"question":  f"Question {question_num}: What is the contact information of {company['name']}?"})
        article["questions"][-1]["answer"] = ""
        if "headquarters" in company:
            article["questions"][-1]["answer"] += f"{company['name']} contact information is {company['headquarters']} as main physical address. "
        if "official_website" in company:
            article["questions"][-1]["answer"] += f"{company['name']} official website address is {company['official_website']}. "
        article["questions"][-1]["answer"] += f"The contact information of {company['name']} is to contact the company for related things to its services and products. To contact {company['name']}, customers can use "
        if "headquarters" in company and "official_website" in company:
            article["questions"][-1]["answer"] += f"{company['headquarters']} and {company['official_website']}."
        elif "headquarters" in company:
            article["questions"][-1]["answer"] += f"{company['headquarters']}."
        else:
            article["questions"][-1]["answer"] += f"{company['official_website']}."
        question_num += 1
    if "headquarters" in company:
        article["questions"].append({"question":  f"Question {question_num}: What is the address of {company['name']}?"})
        article["questions"][-1]["answer"] = ""
        if "number_of_locations" in company:
            article["questions"][-1]["answer"] += f"{company['name']} has {company['number_of_locations']} addresses in its service area"
            if "service_area" in company:
                article["questions"][-1]["answer"] += f" which is {company['service_area']}"
            article["questions"][-1]["answer"] += ". "
        if "country" in company:
            article["questions"][-1]["answer"] += f"The addresses of the {company['name']} are located mainly in {company['country']}. "
        article["questions"][-1]["answer"] += f"{company['name']}'s important addresses are {company['headquarters']}."
        question_num += 1
    article["questions"].append({"question":  f"Question {question_num}: How to Read Reviews about {company['name']}?"})
    article["questions"][-1]["answer"] = f"To read the reviews about {company['name']}, information on the web can be used, and news about the services, and products of {company['name']} can be tracked. Reviews for {company['name']} can include complaints, and general feedback about the company. Complaintsboard.com contains reviews for the {company['name']} by providing the real-world users, and customers of {company['name']} for the "
    if "services" in company:
        article["questions"][-1]["answer"] += f"{oxfordcomma(company['services'][:3])} and more."
    else:
        article["questions"][-1]["answer"] += "high-tech solution and services and more."
    question_num += 1
    article["questions"].append({"question":  f"Question {question_num}: How to write a complaint about {company['name']}?"})
    article["questions"][-1]["answer"] = f"To write a complaint about {company['name']} and take an answer from the officials of {company['name']}, Complaintsboard.com’s objective complaint writing and answer providing system can be used. Product shipment, payment, communication, billing, and any kind of service-related complaint about {company['name']} can be filed via the specific {company['name']} complaints section."
    return article

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Generate articles based on company json data scraped from wikipedia")
    parser.add_argument("input_file", type=str, help="Name of input json file with companies data")
    if len(sys.argv) <= 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    args = parser.parse_args()
    if args.input_file[-5:] != ".json":
        args.output_file += ".json"

    if not os.path.isdir("articles"):
        os.mkdir("articles")

    with open(args.input_file, "r") as f:
        company_data = json.load(f)


    for company in company_data["companies"]:

        print(company['name'])
        article = generate_article(company)
        with open("articles/" + company["name"].replace(".", "").replace(" ", "_").replace("/", "_").replace("\\", "_").replace(",", "_") + ".txt", "w") as f:
            f.write(article)