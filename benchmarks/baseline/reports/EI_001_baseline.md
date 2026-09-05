---
task_id: "b063577a-8e3c-445b-94fc-4c9ec99321c1"
title: "小米手机端AI智能体能力梳理"
query: "梳理小米当前公开披露的手机端 AI Agent / 系统级智能体能力，说明主要功能、技术定位、已落地产品形态。"
report_type: "research_report"
report_source: "web"
tone: "objective"
created_at: "2026-09-05T21:26:22"
sources_count: 19
total_cost_usd: 0.3766
---
# Xiaomi's Publicly Disclosed Mobile AI Agent Capabilities: Functionality, Technical Positioning, and Product Forms of Xiaomi miclaw

## Introduction

As of early September 2026, Xiaomi's most significant publicly disclosed mobile-side AI Agent initiative is **Xiaomi miclaw**, a system-level intelligent agent launched into small-scale closed beta on March 6, 2026 ([Zhidx, 2026](https://m.zhidx.com/p/538251.html)). Industry media have described it as the first mobile-end "lobster" (a developer slang term for OpenClaw-class agents) among Chinese handset vendors ([Guancha, 2026](https://www.guancha.cn/economy/2026_03_06_809060.shtml)). This report consolidates what has been publicly confirmed by Xiaomi's technical team, official developer documentation, and reputable technology media, and separately flags information that remains third-party inference or from unofficial sources. The goal is to provide a comprehensive and objective map of Xiaomi's mobile AI Agent capabilities, their technical positioning, and the product forms that have actually shipped or entered testing.

## Product Overview: Xiaomi miclaw

### Launch Timeline and Availability

Xiaomi's technical team announced Xiaomi miclaw on March 6, 2026, and immediately began an invitation-only, small-scale closed beta test ([Zhidx, 2026](https://m.zhidx.com/p/538251.html); [Guancha, 2026](https://www.guancha.cn/economy/2026_03_06_809060.shtml)). The test was not open to public recruitment and initially supported only the newest Xiaomi 17 series devices, including Xiaomi 17 Ultra Leica Edition, Xiaomi 17 Ultra, Xiaomi 17 Pro Max, Xiaomi 17 Pro, and Xiaomi 17 ([Zhidx, 2026](https://m.zhidx.com/p/538251.html)). Xiaomi explicitly framed the product as an exploratory "mobile AI interaction test product" still being optimized for stability, power consumption, and complex-task execution success rates; some high-complexity tasks may exhibit execution efficiency fluctuation or staged failure ([Zhidx, 2026](https://m.zhidx.com/p/538251.html)). Media coverage also characterized the release as the landing of work associated with AI researcher Luo Fuli, whose team joined Xiaomi's AI efforts ([Zhidx, 2026](https://m.zhidx.com/p/538251.html)).

### Technical Foundation

Xiaomi miclaw is built on Xiaomi's self-developed **MiMo large model** and is designed to deploy large-model execution capabilities at the operating system layer rather than as a standalone conversational application ([Zhidx, 2026](https://m.zhidx.com/p/538251.html)). Third-party technical research places MiMo within a broader Xiaomi model family that includes cloud-based foundation models and end-side lightweight MiLM models (1.3B–6.7B parameters), with end-side inference engineering reportedly reaching around 180 tokens per second ([CSDN openEuler, 2026](https://openeuler.csdn.net/6a7a1ee210ee7a33f2993259.html)). These latter engineering details are analytical reconstructions rather than official Xiaomi disclosures and should be treated with caution.

## Core Functional Capabilities

Multiple independent sources converge on a four-layer capability model for miclaw: **system-level underlying capability, personal context understanding, ecosystem interconnection, and self-evolution mechanism** ([Zhidx, 2026](https://m.zhidx.com/p/538251.html); [Global Sources, 2026](https://www.supplier-globalsources.com/syp/zh/news/details_105392)).

### System-Level Deep Manipulation and Multi-Step Task Automation

Unlike traditional AI assistants that primarily provide information or recommendations, miclaw operates with system-level privileges that allow it to execute physical operations on the phone. It runs as a system-level application and encapsulates more than 50 underlying system tools and ecosystem services ([ai-indeed, 2026](https://www.ai-indeed.com/encyclopedia/17926.html); [Global Sources, 2026](https://www.supplier-globalsources.com/syp/zh/news/details_105392)). The product can autonomously decompose fuzzy user commands into task sequences and execute them step by step, spanning multiple independent applications and system functions ([Zhidx, 2026](https://m.zhidx.com/p/538251.html)).

A representative confirmed scenario: if the user says, "I'm bringing my friend Beibei home in half an hour, get the house ready and give Beibei a warm welcome," the agent automatically infers the intent and coordinates home devices—adjusting lighting, curtains, and air conditioning ([Zhidx, 2026](https://m.zhidx.com/p/538251.html)). Third-party analyses elaborate on a "reasoning–execution" loop engine: upon receiving a ticket-purchase confirmation SMS, the agent can read the message, check the system calendar, set a related alarm, retrieve local weather, and proactively surface a transit QR code ([ai-indeed, 2026](https://www.ai-indeed.com/encyclopedia/17926.html)). These multi-step closed loops cross app boundaries and directly invoke system-level interfaces instead of simulating clicks, which reduces the risk-control problems associated with UI automation ([xiaomimiclaw.net, n.d.](https://xiaomimiclaw.net); [Global Sources, 2026](https://www.supplier-globalsources.com/syp/zh/news/details_105392)).

### Personal Context Memory and Intent Understanding

The second reported layer is personal context understanding. The workflow reportedly shifts from a linear "input–execution" model to a "perception → association → judgment → action" loop ([ai-indeed, 2026](https://www.ai-indeed.com/encyclopedia/17926.html)). For example, when reading a bank deduction notification, the agent can cross-reference local historical billing data and proactively alert the user if it detects characteristics consistent with duplicate charges ([ai-indeed, 2026](https://www.ai-indeed.com/encyclopedia/17926.html)). It is also capable of parsing non-standard, colloquial commands by leveraging local context such as calendar entries and user habits, then deriving concrete system-operation targets ([ai-indeed, 2026](https://www.ai-indeed.com/encyclopedia/17926.html)).

Unofficial technical descriptions add that the agent maintains "file-level memory" for recording user habits and multi-step task state (a capability the fan-documented architecture associates with deep integration of HyperMind) and allows the creation of sub-agents to handle tasks such as schedule management and document summarization, with built-in Python/JavaScript sandboxes for running scripts ([xiaomimiclaw.net, n.d.](https://xiaomimiclaw.net); [CSDN openEuler, 2026](https://openeuler.csdn.net/6a7a1ee210ee7a33f2993259.html)). A third-party technical study describes a "three-level memory" design plus multi-level prompt compression that reportedly saves 50–90% of token overhead in miclaw ([CSDN openEuler, 2026](https://openeuler.csdn.net/6a7a1ee210ee7a33f2993259.html)). These details are not yet confirmed by Xiaomi's official channel and should be read as inferential.

### Cross-Device Ecosystem Scheduling: "Human–Car–Home" Interconnection

A distinguishing attribute of miclaw is its tight integration with Xiaomi's broader hardware ecosystem. Because it fully accesses the Mijia platform, its control scope extends from the phone to a reported base of over 1 billion connected IoT devices ([Global Sources, 2026](https://www.supplier-globalsources.com/syp/zh/news/details_105392); [xiaomimiclaw.net, n.d.](https://xiaomimiclaw.net)). Third-party analysis describes an underlying protocol-conversion mechanism that translates traditional device-control protocols (temperature settings, switch signals) into natural-language interfaces that the large model can directly process ([ai-indeed, 2026](https://www.ai-indeed.com/encyclopedia/17926.html)). Control behaviors are said to be contextually adaptive: when the user says, "I have a meeting, keep quiet," the agent reads the current calendar; if the meeting is with an external client, it silences relevant devices across the home, whereas for an internal weekly meeting it may only mute the phone ([ai-indeed, 2026](https://www.ai-indeed.com/encyclopedia/17926.html)).

### Local Self-Evolution

The fourth layer is a self-evolution mechanism. User preference data and execution histories are reportedly stored in an isolated local sandbox, and as task triggers accumulate, the system engine automatically adjusts the order of system-tool calls and parameter combinations to match user tendencies, producing personalized execution scripts ([ai-indeed, 2026](https://www.ai-indeed.com/encyclopedia/17926.html)). Unofficial sources further claim the agent can "learn" new operation paths for third-party applications and create specialized sub-agents ([xiaomimiclaw.net, n.d.](https://xiaomimiclaw.net); [CSDN openEuler, 2026](https://openeuler.csdn.net/6a7a1ee210ee7a33f2993259.html)). This aligns with industry analyst commentary that AI assistants are shifting from "helping users operate the phone faster" toward "acting on the user's behalf," with applications themselves becoming skill-like service modules invoked by the agent ([TMTPost, n.d.](https://www.tmtpost.com/8078891.html)).

The table below summarizes the principal reported capabilities and their evidentiary basis:

| Capability domain | Representative functionality | Sources | Confirmation status |
|---|---|---|---|
| System-level manipulation | 50+ system tools; cross-app multi-step execution; native system-UID operation | Zhidx, Global Sources, ai-indeed | Confirmed by multiple outlets; details third-party |
| Personal context memory | SMS/calendar/context reading; "perceive–associate–judge–act" loop | ai-indeed, Zhidx | Partially confirmed; mechanisms inferred |
| Ecosystem interconnection | Mijia IoT control; scenario-based device orchestration | Global Sources, Zhidx | Confirmed scenario; 1B device figure from secondary sources |
| Self-evolution | Local sandbox; execution-path optimization; sub-agent creation | ai-indeed, CSDN openEuler | Third-party inference; not officially detailed |

## Technical Architecture and OS-Level Positioning

### HyperOS 4 as the AI-Native Foundation

Xiaomi miclaw does not exist in isolation; it sits atop a deeper operating-system transformation. In March 2026, Xiaomi shipped **HyperOS 4**, which reportedly removed the MIUI transition layer, cleared legacy code modules, adopted Flutter for unified UI rendering, and used Rust to strengthen core-logic security ([CSDN openEuler, 2026](https://openeuler.csdn.net/6a7a1ee210ee7a33f2993259.html)). The decisive architectural shift is that "AI capabilities are integrated into the system framework rather than deployed as a standalone application"—resource scheduling is reorganized around AI, while Android native service compatibility is retained ([CSDN openEuler, 2026](https://openeuler.csdn.net/6a7a1ee210ee7a33f2993259.html)). A third-party study characterizes this as an OS-level AI-native reconstruction, arguing that Xiaomi avoided the "AI wrapper" failure pattern by rebuilding the system rather than overlaying a chatbot onto the old stack ([CSDN openEuler, 2026](https://openeuler.csdn.net/6a7a1ee210ee7a33f2993259.html)). This source is a third-party academic/industry analysis, and its internal architecture claims are explicitly flagged by the authors as partly inferred from product behavior.

### Agent Developer Ecosystem and a New Distribution Channel

Xiaomi's official HyperOS developer platform confirms a concrete, shipped product form around the agent: the **Agent ecosystem**. Developers can register "Agent applications" through the Xiaomi HyperOS Developer Platform's management console, and these Agent applications are explicitly stated to be **distributable only within Miclaw** ([Xiaomi HyperOS Developer Platform, 2026](https://dev.mi.com/xiaomihyperos/documentation/detail?pId=2305)). The creation flow is itself agentic: developers describe the Agent's name, role description, and icon, and then generate the Agent by sending natural-language prompts—with optional file attachments—into an online Agent development platform. The platform generates a workspace containing Prompt, Config, and Profile files, along with Tools, Skill, and Memory folders, all of which developers can inspect and modify ([Xiaomi HyperOS Developer Platform, 2026](https://dev.mi.com/xiaomihyperos/documentation/detail?pId=2305)). This indicates that Xiaomi is treating the agent runtime as a new app-distribution surface, analogous to an "app store for agents," which is a substantial and officially confirmed product-form evolution.

Third-party technical research adds that this ecosystem access is provided through two channels—an MCP protocol channel and an open SDK—with a full Mijia protocol client enabling authorized control of Mijia IoT devices ([CSDN openEuler, 2026](https://openeuler.csdn.net/6a7a1ee210ee7a33f2993259.html)). The MCP detail has not been confirmed in official documentation provided to date and should be treated as analytical inference, though the Model Context Protocol is a widely adopted industry standard.

### The Broader Xiaomi Agent Matrix

Xiaomi's mobile agent is one node in a wider cross-domain agent matrix described in third-party research: **Xiaomi miclaw** on phones (MiMo model), **XLA** cognitive large model in automobiles (unifying multimodal input toward embodied-robot foundations), **Miloco** for the home (moving from rule-driven automation to AI-autonomous orchestration), and **Xiaomi-Robotics-0** for embodied intelligence ([CSDN openEuler, 2026](https://openeuler.csdn.net/6a7a1ee210ee7a33f2993259.html)). The same analysis recommends a phased path "from system-level agent (miclaw model), to cross-device agents (XLA/Miloco), and finally embodied agents"—though this is presented as the analyst's methodology rather than Xiaomi's official roadmap.

## Security, Privacy, and Safety Design

Because miclaw possesses system-level execution privileges, Xiaomi has emphasized a layered safety architecture. According to industry media relaying Xiaomi technical team communications, sensitive operations trigger a confirmation popup on every occurrence; if the user does not act within 60 seconds, the operation is automatically rejected; high-risk tools such as payment and transfer functions are not exposed to the agent ([Global Sources, 2026](https://www.supplier-globalsources.com/syp/zh/news/details_105392)). Conversation records are kept locally, and the cloud transmits only necessary information, which is deleted after use ([Global Sources, 2026](https://www.supplier-globalsources.com/syp/zh/news/details_105392)). The fan-maintained FAQ adds that sensitive permissions—contacts, SMS, calendar—require runtime user granting, and high-risk actions such as sending SMS or creating calendar entries require user confirmation ([xiaomimiclaw.net, n.d.](https://xiaomimiclaw.net)). These safety measures are contextualized by industry-reported incidents in the broader OpenClaw ecosystem, where an "instruction forgetting" bug led to unintended bulk email deletion when an agent's context-compression mechanism dropped a user's explicit "advice-only, do not operate" instruction ([Global Sources, 2026](https://www.supplier-globalsources.com/syp/zh/news/details_105392)).

Third-party research further notes that China's端侧 large-model filing regime matured in 2026, with Xiaomi among seven vendors (including Huawei and Apple) completing end-side model filing around July 8, 2026, and that Xiaomi has stated it will not rush commercial monetization of AI tokens, preferring to treat AI capabilities as long-term infrastructure ([CSDN openEuler, 2026](https://openeuler.csdn.net/6a7a1ee210ee7a33f2993259.html)). The same source describes a "Token Plan" introduced in Q1 2026 that meters AI capability usage by token consumption ([CSDN openEuler, 2026](https://openeuler.csdn.net/6a7a1ee210ee7a33f2993259.html)).

## Industry Context and Standards Alignment

Xiaomi's mobile agent push aligns with a broader industry transition. Under China's national terminal-intelligence grading standard, which runs from L1 to L4, **L3** requires "complex intent understanding, complex chain reasoning and task planning, automatic multi-step tool calling, and long-term memory." In the first batch of testing, phones from StepFun, Huawei, Xiaomi, OPPO, Honor, vivo, and Lenovo all reached the L3 level ([TMTPost, n.d.](https://www.tmtpost.com/8078891.html)). Industry observers describe the evolution from 1.0 single-point AI tools and 2.0 system-level assistants toward 3.0 autonomous agents, in which the OS itself becomes agentized while traditional apps are progressively "skill-ified" into callable capability interfaces ([TMTPost, n.d.](https://www.tmtpost.com/8078891.html)). At the silicon level, MediaTek's Dimensity Developer Conference in May 2026 reported that agentic AI autonomous task volumes on devices grew roughly sevenfold year over year, from 120 million to 870 million daily tasks ([QbitAI, 2026](https://www.qbitai.com/2026/05/417968.html)). Xiaomi's miclaw is therefore part of an ecosystem-wide race to make end-side agents the primary interaction paradigm.

This evolution also has direct lineage from Xiaomi's earlier voice-assistant efforts: "Xiao Ai Tong Xue" (小爱同学), launched in 2017, had already accumulated over 10 billion voice interactions by June 2019 across smart speakers and phones, with IoT device control as a core function ([OFweek, 2019](https://m.ofweek.com/ai/2019-06/ART-201719-8110-30390355.html)). Xiaomi's official speaker product pages show that Xiao Ai's conversational command set (alarms, weather, traffic, device control, content playback) provided the foundational human–machine interaction layer upon which the company's agent strategy now builds ([Xiaomi Mall, n.d.](https://www.mi.com/aispeaker); [Xiaomi Mall, n.d.](https://www.mi.com/aispeaker-play)).

## Boundaries Between Confirmed and Speculative Information

For readers assessing reliability, the following classification is useful:

**Publicly confirmed or multiply corroborated:** the existence, naming, launch date, and beta scope of Xiaomi miclaw; its basis on the MiMo model; support for Xiaomi 17 series; the 50+ system tool claim; the four-layer capability framing; the "welcome Beibei home" scenario; the invitation-only testing model; developer Agent applications being distributable only in Miclaw; and the general security design (runtime permission grants, user confirmation, no payment tools).

**Third-party inference or unofficial:** the specific "three-level memory" mechanism, MCP protocol usage, Python/JavaScript sandbox claims, sub-agent creation details, the 1 billion IoT device figure, the 180 tokens/s inference figure, the Token Plan's revenue structure, and HyperMind integration specifics. These appear in fan-maintained sites or analytical reconstructions that themselves acknowledge inference ([xiaomimiclaw.net, n.d.](https://xiaomimiclaw.net); [CSDN openEuler, 2026](https://openeuler.csdn.net/6a7a1ee210ee7a33f2993259.html)). The fan site explicitly disclaims official status ([xiaomimiclaw.net, n.d.](https://xiaomimiclaw.net)).

## Concluding Assessment

Xiaomi's publicly disclosed mobile AI Agent capability, as of September 2026, is best summarized as a **system-level, end-cloud collaborative execution engine** anchored by Xiaomi miclaw, an invitation-only test product running on Xiaomi 17 series phones and built on the MiMo foundation model. Its confirmed distinctiveness lies in three directions: (1) direct invocation of 50+ system-level tools enabling cross-app task execution rather than conversational advice; (2) deep coupling with Xiaomi's "Human–Car–Home" IoT fleet for physical-world control; and (3) an OS-level ecosystem play in which HyperOS 4 embeds AI into the system framework and third-party Agent applications are distributed through miclaw. The reported self-evolution, contextual memory, and multi-agent orchestration capabilities are plausible and technically coherent, but remain primarily documented through secondary and unofficial channels. Overall, Xiaomi appears to be deliberately sequencing its agent rollout: system-level agent first, ecosystem distribution second, and monetization later—consistent with its stated position that AI is infrastructure to be built patiently rather than commercialized hastily.

## References

ai-indeed. (2026, June 30). *Miclaw能干啥？Miclaw可以干什么？小米端侧原生智能体能力解析*. 实在智能. [https://www.ai-indeed.com/encyclopedia/17926.html](https://www.ai-indeed.com/encyclopedia/17926.html)

CSDN openEuler. (2026, August 11). *传统企业技术中台向 AI Native 中台演进路线与方法论*. [https://openeuler.csdn.net/6a7a1ee210ee7a33f2993259.html](https://openeuler.csdn.net/6a7a1ee210ee7a33f2993259.html)

Global Sources. (2026, March 10). *小米落地端侧AI智能体Xiaomi miclaw，移动电子厂商迎来硬件升级与价值重估新机遇*. [https://www.supplier-globalsources.com/syp/zh/news/details_105392](https://www.supplier-globalsources.com/syp/zh/news/details_105392)

Guancha. (2026, March 6). *首款移动端"龙虾"来了，小米miclaw开启小范围封测*. 观察者网. [https://www.guancha.cn/economy/2026_03_06_809060.shtml](https://www.guancha.cn/economy/2026_03_06_809060.shtml)

OFweek. (2019, June 5). *史上最成功智能音箱 小爱同学交互破百亿次*. [https://m.ofweek.com/ai/2019-06/ART-201719-8110-30390355.html](https://m.ofweek.com/ai/2019-06/ART-201719-8110-30390355.html)

QbitAI. (2026, May). *手机的智能体AI，正在因为天玑全面跃升*. 量子位. [https://www.qbitai.com/2026/05/417968.html](https://www.qbitai.com/2026/05/417968.html)

TMTPost. (n.d.). *Agent手机的三条路线与一场权力游戏*. 钛媒体. [https://www.tmtpost.com/8078891.html](https://www.tmtpost.com/8078891.html)

Xiaomi HyperOS Developer Platform. (2026, April 28). *Agent应用发布操作指南*. 小米澎湃OS开发者平台. [https://dev.mi.com/xiaomihyperos/documentation/detail?pId=2305](https://dev.mi.com/xiaomihyperos/documentation/detail?pId=2305)

Xiaomi Mall. (n.d.). *小米AI音箱*. [https://www.mi.com/aispeaker](https://www.mi.com/aispeaker)

Xiaomi Mall. (n.d.). *小米小爱音箱 Play版*. [https://www.mi.com/aispeaker-play](https://www.mi.com/aispeaker-play)

xiaomimiclaw.net. (n.d.). *小米Xiaomi Miclaw - 系统级AI智能体* (粉丝站点). [https://xiaomimiclaw.net](https://xiaomimiclaw.net)

Zhidx. (2026, March 6). *小米版OpenClaw来了！手机就能养龙虾，罗福莉成果落地*. 智东西. [https://m.zhidx.com/p/538251.html](https://m.zhidx.com/p/538251.html)