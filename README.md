# Intro

Welcome to my showcase. In this repo I will discuss my work as a developer.
I'll try to include designs from my past and present, and discuss my future plans.
I also care about customization and developer workflows, and I will also discuss those here.

# Structure 

Since the repo is very new I haven't decided on a good structure yet. What I will do is
write individual README's that explain parts of the code included. And have subcontent sections
that explain parts of my work.

# Dev Content

I have included examples of code that explains some of the designs that I/we've
built. Please notice that the code won't work since I've removed all
relative/internal imports because of IPR.

Now I will move on to the juicy parts. Enjoy :)

## Architecture/Backend/Python

I/We have constructed a backend in Python which is centered around a document-processing
pipeline that utilizes machine learning, natural language processing and searching.
The backend is scalable (supports >1M documents of sizes up to 50MB), well-tested and maintainable.
Since the software is proprietary, I can only show you snippets of the code that explain the general idea.
You can find the snippets and more detailed explanations (when I make those) in the `lib/` folder.

The basic principles of the architecture are: blocking low-cost operations API -> asynchronous
task-based library picked up for longer-running tasks -> web-socket based notifications for real-time 
updating client consumers when changes happen in the backend. 
 
In Python, we liked using a lightweight combination of Flask + Celery which is built on Docker images and easily
deployed on different architectures. I will expand on the deployment in the CI section.

## AI / ML

My primary specialization at the university centered around advances in Natural Language Processing (NLP) with Deep Learning (DL).
The result of that specialization is mainly:

- A bachelor thesis, for which I received the highest grade 12.
- A graduate thesis, for which I received the highest grade. You can find the repository here: https://github.com/msta/cnn_rc/ and the associated report: https://github.com/msta/cnn_rc/blob/master/ThesisMSTA2017.pdf
- The opportunity to apply machine learning in production by designing, implementing and deploying a document classification and enrichment model to production for 3 years

My focused work in this area after the university have been to recognize the challenges and pitfalls in getting ML to production.
To that end I've spent time on managing resources for training data, selecting simple models with good reasonability, implementing
probability scores for customers to understand predictions, connected ML models to DevOps and other engineering efforts,
and redesigned implementations to reduce memory footprints and improve performance. You can see some of
this work in `lib/`.


## DevOps / Kubernetes / Cloud-first

My main work in DevOps have been around trying to build a CD pipeline and deploying stacks
to orchestrated environments (Kubernetes). To that end I've built some experience in deploying
architecture with code (Terraform). We have built a one-click deployable stack with:

- Automatically setup kubernetes cluster
- The cluster is setup with certificates, RBAC, Prometheus, Kibana and Grafana for monitoring and logging.
- The stack is then deployed onto the cluster, including customly built Helm charts such as ElasticSearch and our own Stack
- Managed services are generated with Terraform and linked to the cluster
- The services are automatically DNS-registered on CLoudflare so they are easily accessible. 



## Structure/Process and Leadership

I think this area is better discussed orally. But to sum up, I have:

- Led a team of 4-7 developers for about 2 years
- Used SCRUM and Kanban with various success, and been Scrum Master for a good part of that process
- I strongly believe in WIP limits as essential for releasing fast
- Gained heavy interest in combining agile development methods with lean thinking, mainly how validation should be
an essential part of any task board.
- Ran several handfuls of interviews and recruited developers from various parts of the world.


## Customization / Workflow

I like to setup and customize my own environment. I'm only a novice in this area, 
so I'd really like suggestions. 

- I run on Ubuntu 16.04 but I'd like to explore other Linux distributions.
- I built an Ergodox Infinity and uses a modified QWERTY-mapping mainly for Python development
- I use JetBrains IDEs and oh-my-zsh for editing
- Getting into cloud-first development with AWS Devtools like Cloud9








