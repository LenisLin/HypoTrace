# Identification of hypoxic macrophages in glioblastoma with therapeutic potential for vasculature normalization

> Analysis Logic Chain。它聚焦 Agent 可执行的数据分析方法路径；文章中不属于数据分析方法的验证或背景内容只作为上下文记录。

## Paper Overview

- 核心问题：如何从 glioma scRNA-seq 和 spatial transcriptomics 中识别 Hypoxia-TAM，并把它推进到候选分泌因子 ADM？
- 主线：scRNA-seq 状态发现 -> Mo-TAM signature / pathway 注释 -> spatial mapping -> histology niche association -> hypoxia / interaction / secreted factor candidate prioritization。
- 结构：Paper -> Chain Question -> Connected Logic Steps。
- 机器输入：`examples/gbm_hypoxia_tam_reference_demo/analysis_logic_chain.jsonl`

## Data Backbone / Availability

| 数据 | 用途 | 获取信息 |
| --- | --- | --- |
| Human glioma scRNA-seq | 发现 Mo-TAM 状态 | NGDC PRJCA008116; human scRNA-seq: OMIX002713；文章声明发表时公开。 |
| Public hGBM Visium spatial transcriptomics | 把 Mo-TAM 状态映射回组织空间 | Dryad、GEO GSE194329、PRJCA015974 / OMIX003593 等来源。 |
| IvyGBM / TCGA bulk RNA-seq | bulk deconvolution 与 ADM-associated GSEA | IvyGBM Atlas Project 与 TCGA/GDC 为公共来源。 |

## Bioinformatics Chain Overview

### 从 scRNA-seq 到 Mo-TAM 状态定义

- Chain ID：`C1_SCRNA_TO_MOTAM_STATE`
- Chain order：1
- 分析问题：如何从 diffuse glioma scRNA-seq 中得到可追踪的 Mo-TAM 状态，尤其是 Hypoxia-TAM？
- 短问题：How is Hypoxia-TAM defined from scRNA-seq?
- 路线：
  - `START` -> `C1_S01` -> `C1_S02`：scRNA-seq QC and malignant/non-malignant separation
  - `C1_S01` -> `C1_S02` -> `C1_S03`：Batch correction, dimensional reduction, and clustering
  - `C1_S02` -> `C1_S03` -> `C1_S04`：Mo-TAM cluster marker detection
  - `C1_S03` -> `C1_S04` -> `C1_S05`：Myeloid-specific marker detection
  - `C1_S04` -> `C1_S05` -> `C1_S06`：Mo-TAM core signature construction
  - `C1_S05` -> `C1_S06` -> `C1_S07`：GSVA pathway annotation of Mo-TAM clusters
  - `C1_S06` -> `C1_S07` -> `END`：Hypoxia-TAM state identification from marker and pathway evidence

### 从 Mo-TAM 状态到空间生态位定位

- Chain ID：`C2_MOTAM_TO_SPATIAL_NICHE`
- Chain order：2
- 分析问题：Hypoxia-TAM 是否定位于 hGBM 的特定组织空间生态位？
- 短问题：Where is Hypoxia-TAM located in tissue?
- 依赖链：`C1_SCRNA_TO_MOTAM_STATE`
- 路线：
  - `START` -> `C2_S01` -> `C2_S02`：Public Visium preprocessing and image alignment
  - `C2_S01` -> `C2_S02` -> `C2_S03`：Visium spot QC and normalization
  - `C2_S02` -> `C2_S03` -> `C2_S04`：Cell2location reference model construction
  - `C2_S03` -> `C2_S04` -> `C2_S05`：Spatial spot-level Mo-TAM decomposition
  - `C2_S04` -> `C2_S05` -> `C2_S06`：Histology-region assignment to spatial spots
  - `C2_S05` -> `C2_S06` -> `END`：Region-level Mo-TAM enrichment analysis

### 从 Hypoxia-TAM 到候选机制优先级排序

- Chain ID：`C3_HYPOXIA_TAM_TO_CANDIDATE_PRIORITIZATION`
- Chain order：3
- 分析问题：哪些 Hypoxia-TAM 相关基因或通讯因子值得进入后续机制验证？
- 短问题：Which Hypoxia-TAM factor should be prioritized?
- 依赖链：`C1_SCRNA_TO_MOTAM_STATE`, `C2_MOTAM_TO_SPATIAL_NICHE`
- 路线：
  - `START` -> `C3_S01` -> `C3_S02`：Hypoxia-associated gene set construction
  - `C3_S01` -> `C3_S02` -> `C3_S03`：Functional network annotation of hypoxia-associated genes
  - `C3_S02` -> `C3_S03` -> `C3_S04`：SCENIC regulon analysis
  - `C3_S03` -> `C3_S04` -> `C3_S05`：EC-Mo-TAM ligand-receptor interaction analysis
  - `C3_S04` -> `C3_S05` -> `END`：ADM candidate prioritization from Hypoxia-TAM secreted factors

## Intermediate Task Breakdown

| Step | 中程问题 | 证据等级 | 输入数据 | 直接产出 | 下一步理由 |
| --- | --- | --- | --- | --- | --- |
| `C1_S01` | 测试后续 myeloid / Mo-TAM 分析是否建立在可用且对象边界清楚的 scRNA-seq 数据上。 | `preprocessing` | Human glioma scRNA-seq dataset | 得到更适合后续细胞状态建模的 scRNA-seq cell set。 | 在对象边界清楚后，下一步需要校正样本差异并建立细胞状态结构。 |
| `C1_S02` | 测试 scRNA-seq 数据中是否存在可分离的细胞 cluster / Mo-TAM cluster 结构。 | `preprocessing` | QC-filtered scRNA-seq cells | 得到后续可注释的 cell cluster / Mo-TAM cluster structure。 | 下一步需要找到每个 Mo-TAM cluster 的 marker，以判断这些 cluster 代表什么状态。 |
| `C1_S03` | 测试每个 Mo-TAM cluster 是否有可区分的 marker gene program。 | `association` | Mo-TAM clusters from hGBM scRNA-seq | 得到每个 Mo-TAM cluster 的候选 marker set。 | 下一步需要识别 myeloid-specific alterations，使 signature 更适合代表 Mo-TAM 状态。 |
| `C1_S04` | 测试哪些表达特征能代表 myeloid / Mo-TAM identity，而不是只代表某个 cluster 内差异。 | `association` | Myeloid cells and other cell types in hGBM scRNA-seq | 得到可用于限制 Mo-TAM signature 的 myeloid-specific marker evidence。 | 下一步可以将 cluster-specific 与 myeloid-specific evidence 取交集构建 core signature。 |
| `C1_S05` | 测试哪些 genes 同时代表 Mo-TAM cluster specificity 和 myeloid relevance。 | `association` | Mo-TAM cluster-specific alterations<br>Myeloid-specific alterations | 得到可作为 reference 的 Mo-TAM cluster core signatures。 | 下一步需要用 pathway analysis 解释这些 Mo-TAM states 的功能差异。 |
| `C1_S06` | 测试 Mo-TAM clusters 是否具有不同的 pathway programs。 | `enrichment` | Single-cell count matrix<br>MSigDB C2/C5 gene sets<br>Mo-TAM clusters | 得到 Mo-TAM cluster-level pathway programs。 | 下一步可以结合 marker 和 pathway evidence 判断是否存在 hypoxia-associated Mo-TAM state。 |
| `C1_S07` | 测试是否存在一个可被 marker/pathway evidence 支持的 hypoxia-associated Mo-TAM state。 | `enrichment` | Mo-TAM cluster markers<br>Mo-TAM pathway programs | 一个 Mo-TAM cluster 被 marker/pathway evidence 区分为 hypoxia-associated state。 | 下一步需要把 Hypoxia-TAM 映射回组织空间，测试它是否位于 peri-necrotic / hypoxic niche。 |
| `C2_S01` | 测试公共 hGBM Visium 数据是否能被整理为空间表达矩阵和图像对齐对象。 | `preprocessing` | Public hGBM Visium spatial transcriptomics datasets<br>Paired histology images | 得到后续 Seurat/Cell2location 可使用的空间表达矩阵和 spot-image alignment。 | 下一步需要对 spot 质量和 normalization 做处理，确保空间映射不受低质量 spots 影响。 |
| `C2_S02` | 测试哪些 hGBM spatial samples 和 spots 可用于后续空间映射。 | `preprocessing` | SpaceRanger outputs<br>Visium spots<br>Paired images | 得到 QC 后的 hGBM spatial transcriptomic dataset。 | 下一步可以用 scRNA-derived Mo-TAM signatures 建立 Cell2location reference。 |
| `C2_S03` | 测试 scRNA-defined Mo-TAM states 是否能作为 spatial decomposition 的 reference。 | `spatial_mapping` | Annotated Mo-TAM clusters from scRNA-seq<br>Mo-TAM signatures | 得到用于 spatial decomposition 的 Mo-TAM reference signature model。 | 下一步用 reference model 分解每个 spatial spot 的 Mo-TAM cluster proportion。 |
| `C2_S04` | 测试 scRNA-defined Mo-TAM states 能否被投射到 spatial spots。 | `spatial_mapping` | QC-normalized Visium count matrices<br>Cell2location reference signature model | 得到 spot-level Mo-TAM composition estimates。 | 下一步需要把 spot-level composition 与 histology regions 对齐，判断空间生态位。 |
| `C2_S05` | 测试每个 spatial spot 是否能获得可比较的 histology region label。 | `spatial_mapping` | H&E images<br>Spatial spots<br>Ivy hGBM histology categories | 得到带有 histology region labels 的 spatial spots。 | 下一步可以计算每个 region 中 Mo-TAM cluster proportion 的均值并比较富集。 |
| `C2_S06` | 测试 Hypoxia-TAM 是否在 peri-necrotic region 中富集。 | `association` | Spot-level Mo-TAM proportions<br>Spot-level histology region labels | Hypoxia-TAM 获得 peri-necrotic spatial niche association。 | 下一步可以问：这个 niche-associated Hypoxia-TAM 是否有与 hypoxia 和 vascular remodeling 相关的候选基因或通讯因子。 |
| `C3_S01` | 测试哪些 genes 同时与 Hypoxia-TAM upregulation 和 hypoxia score 相关。 | `association` | Hypoxia-TAM upregulated genes<br>HARRIS_HYPOXIA gene set<br>Hypoxia-TAM single-cell expression | 得到 Hypoxia-TAM hypoxia-associated gene candidates。 | 下一步需要把这些候选 genes 组织成 interaction / functional network。 |
| `C3_S02` | 测试 hypoxia-associated genes 是否形成可解释的 functional interaction network。 | `network_support` | Core HRGs<br>HPGs<br>HNGs | 得到 Hypoxia-TAM hypoxia-associated gene interaction network。 | 下一步可以进一步推断调控这些 Hypoxia-TAM programs 的 TF/regulon。 |
| `C3_S03` | 测试 Mo-TAM clusters 是否具有不同 TF regulon activity，哪些 TF 可能关联 Hypoxia-TAM signature。 | `network_support` | Mo-TAM scRNA-seq expression matrix<br>Mo-TAM cells from necrotic hGBM cases | 得到 Mo-TAM regulon activity landscape。 | 下一步可以结合 cell-cell interaction 或 secreted factor screening 寻找 Hypoxia-TAM 影响其他细胞的候选通讯因子。 |
| `C3_S04` | 测试 Hypoxia-TAM / Mo-TAM clusters 是否具有与 ECs 的候选 ligand-receptor communication。 | `network_support` | ECs in hGBM scRNA-seq<br>Mo-TAM clusters in hGBM scRNA-seq | 得到 EC-Mo-TAM candidate communication map。 | 下一步可与 secreted protein / hypoxia response / Hypoxia-TAM signature 交集筛选结合，优先级排序具体候选因子。 |
| `C3_S05` | 测试是否存在一个由 Hypoxia-TAM 表达、具备分泌属性、且与 hypoxia response 相连的优先候选。 | `candidate_prioritization` | Hypoxia-TAM signature genes<br>Human secreted protein genes<br>Hypoxia response gene set | ADM 被计算优先级排序为文章后续验证的候选因子。 | 后续验证可以作为文章整体逻辑上下文记录，但不属于 Agent 可执行的数据分析方法路径。 |

## Step Details

### 从 scRNA-seq 到 Mo-TAM 状态定义

#### C1_S01 scRNA-seq QC and malignant/non-malignant separation

- 连接：`START` -> `C1_S01` -> `C1_S02`
- 证据等级：`preprocessing`
- Gold confidence：`medium`

**分析问题**

测试后续 myeloid / Mo-TAM 分析是否建立在可用且对象边界清楚的 scRNA-seq 数据上。

**输入数据**

- Human glioma scRNA-seq dataset

**为什么做这一步**

如果低质量细胞、极端基因数细胞或 malignant cells 没有被处理，后续 TAM 状态会混入技术噪声或肿瘤细胞信号。

**分析任务**

过滤低表达基因和异常细胞，并用 inferCNV 区分 malignant 与 non-malignant cells。

**观察到的数据证据**

- 低表达基因和异常细胞被排除。
- inferCNV 提供 malignant / non-malignant cell separation。

**分析得到什么**

得到更适合后续细胞状态建模的 scRNA-seq cell set。

**生物学解释**

这一步不是发现 Hypoxia-TAM，而是建立后续 TAM 分析对象的质量和细胞边界。

**证据如何推进**

分析从原始单细胞数据推进到可用于降维、聚类和髓系细胞分析的细胞集合。

**下一步为什么出现**

在对象边界清楚后，下一步需要校正样本差异并建立细胞状态结构。

**解释边界**

QC 和 inferCNV 不能定义 TAM 状态，只能减少明显噪声和 malignant signal contamination。

**证据锚点**

- p.26；STAR Methods；`inferCNV`：方法描述过滤基因/细胞、线粒体比例阈值，并用 inferCNV 区分 malignant 与 non-malignant cells。

**审查提醒**

- 不要把 QC 后的数据对象写成 biological discovery。

#### C1_S02 Batch correction, dimensional reduction, and clustering

- 连接：`C1_S01` -> `C1_S02` -> `C1_S03`
- 证据等级：`preprocessing`
- Gold confidence：`medium`

**分析问题**

测试 scRNA-seq 数据中是否存在可分离的细胞 cluster / Mo-TAM cluster 结构。

**输入数据**

- QC-filtered scRNA-seq cells

**为什么做这一步**

要发现可比较的细胞状态，需要先缓解样本批次差异，再在低维空间中聚类。

**分析任务**

使用 Harmony 缓解 batch effect，基于 2,000 highly variable genes 做 PCA，用前 20 PCs 生成 UMAP，并用 Seurat FindClusters 聚类。

**观察到的数据证据**

- 样本 batch effect 被 Harmony 处理。
- PCA/UMAP/FindClusters 生成细胞聚类结构。

**分析得到什么**

得到后续可注释的 cell cluster / Mo-TAM cluster structure。

**生物学解释**

聚类结构本身只是计算分组，仍需要 marker 和 pathway 证据解释其生物含义。

**证据如何推进**

分析从可用细胞集合推进到可比较的细胞状态候选结构。

**下一步为什么出现**

下一步需要找到每个 Mo-TAM cluster 的 marker，以判断这些 cluster 代表什么状态。

**解释边界**

聚类 resolution 和前 20 PCs 会影响 cluster 结构；cluster 不是自动等同于生物状态。

**证据锚点**

- p.26；STAR Methods；`FindClusters`：方法描述 Harmony、PCA、UMAP 和 FindClusters resolution 0.4。

**审查提醒**

- 不要把 UMAP cluster 直接写成已解释的生物状态。

#### C1_S03 Mo-TAM cluster marker detection

- 连接：`C1_S02` -> `C1_S03` -> `C1_S04`
- 证据等级：`association`
- Gold confidence：`medium`

**分析问题**

测试每个 Mo-TAM cluster 是否有可区分的 marker gene program。

**输入数据**

- Mo-TAM clusters from hGBM scRNA-seq

**为什么做这一步**

要解释每个 Mo-TAM cluster，需要先找出相对于其他 Mo-TAM clusters 上调的 cluster-specific alterations。

**分析任务**

使用 Seurat FindAllMarkers 识别 Mo-TAM cluster-specific alterations。

**观察到的数据证据**

- 每个 Mo-TAM cluster 有 cluster-specific alterations。
- 阈值包括 fold change >= 1.5 和 adjusted p < 0.05。

**分析得到什么**

得到每个 Mo-TAM cluster 的候选 marker set。

**生物学解释**

这些 marker 说明 cluster 之间有表达差异，但还需要排除非髓系或泛细胞信号。

**证据如何推进**

分析从 cluster structure 推进到 cluster-specific expression evidence。

**下一步为什么出现**

下一步需要识别 myeloid-specific alterations，使 signature 更适合代表 Mo-TAM 状态。

**解释边界**

cluster-specific marker 可能包含非髓系背景或技术相关信号，需要与 myeloid-specific evidence 结合。

**证据锚点**

- p.26；STAR Methods；`cluster-specific alterations`：方法说明用 FindAllMarkers 识别 Mo-TAM cluster-specific alterations 及阈值。

**审查提醒**

- 不要只凭 marker list 给出机制解释。

#### C1_S04 Myeloid-specific marker detection

- 连接：`C1_S03` -> `C1_S04` -> `C1_S05`
- 证据等级：`association`
- Gold confidence：`medium`

**分析问题**

测试哪些表达特征能代表 myeloid / Mo-TAM identity，而不是只代表某个 cluster 内差异。

**输入数据**

- Myeloid cells and other cell types in hGBM scRNA-seq

**为什么做这一步**

如果不限定 myeloid-specific alterations，后续 deconvolution / spatial mapping 可能受泛细胞表达影响。

**分析任务**

使用 FindAllMarkers 识别 myeloid-specific alterations，即 myeloid cells 相对其他 cell types 上调的 genes。

**观察到的数据证据**

- myeloid-specific alterations 被独立识别。
- 阈值包含 pct difference、fold change、adjusted p 和 cell type 内表达比例。

**分析得到什么**

得到可用于限制 Mo-TAM signature 的 myeloid-specific marker evidence。

**生物学解释**

这些特征帮助将 Mo-TAM 状态与整体 myeloid identity 联系起来。

**证据如何推进**

分析从单纯 cluster marker 推进到 Mo-TAM identity-aware marker evidence。

**下一步为什么出现**

下一步可以将 cluster-specific 与 myeloid-specific evidence 取交集构建 core signature。

**解释边界**

myeloid-specific marker 仍是差异表达结果，不代表空间定位或机制功能。

**证据锚点**

- p.26；STAR Methods；`myeloid-specific alterations`：方法说明 myeloid-specific alterations 的 FindAllMarkers 阈值。

**审查提醒**

- 不要把 myeloid-specific marker 写成 Mo-TAM cluster 的最终功能解释。

#### C1_S05 Mo-TAM core signature construction

- 连接：`C1_S04` -> `C1_S05` -> `C1_S06`
- 证据等级：`association`
- Gold confidence：`medium`

**分析问题**

测试哪些 genes 同时代表 Mo-TAM cluster specificity 和 myeloid relevance。

**输入数据**

- Mo-TAM cluster-specific alterations
- Myeloid-specific alterations

**为什么做这一步**

要让 Mo-TAM cluster 能被 bulk deconvolution 或 spatial mapping 使用，需要提取更稳定的 core signature。

**分析任务**

将 cluster-specific alterations 与 myeloid-specific alterations 取交集，构建每个 Mo-TAM cluster 的 core signature。

**观察到的数据证据**

- 每个 Mo-TAM cluster 获得 core gene signature。
- core signature 来源于 cluster-specific alterations 与 myeloid-specific alterations 的交集。

**分析得到什么**

得到可作为 reference 的 Mo-TAM cluster core signatures。

**生物学解释**

这些 signature 将 UMAP cluster 转化为可追踪的状态定义。

**证据如何推进**

分析从 marker evidence 推进到可用于 deconvolution / spatial mapping 的 reference signature。

**下一步为什么出现**

下一步需要用 pathway analysis 解释这些 Mo-TAM states 的功能差异。

**解释边界**

交集 signature 提高状态可追踪性，但不证明功能因果。

**证据锚点**

- p.26；STAR Methods；`core gene signature`：方法说明 core gene signature 由两类 alterations 交集提取。

**审查提醒**

- signature 是状态追踪工具，不是机制证明。

#### C1_S06 GSVA pathway annotation of Mo-TAM clusters

- 连接：`C1_S05` -> `C1_S06` -> `C1_S07`
- 证据等级：`enrichment`
- Gold confidence：`medium`

**分析问题**

测试 Mo-TAM clusters 是否具有不同的 pathway programs。

**输入数据**

- Single-cell count matrix
- MSigDB C2/C5 gene sets
- Mo-TAM clusters

**为什么做这一步**

为了判断哪个 Mo-TAM cluster 与 hypoxia、glycolysis、angiogenesis 等程序相关，需要对 cluster 做 pathway-level 注释。

**分析任务**

使用 MSigDB C2/C5 gene sets 和 GSVA，对 single-cell count matrix 计算 z-score，并用 FindAllMarkers 识别 cluster core pathways。

**观察到的数据证据**

- 每个细胞获得 GSVA z-score matrix。
- core pathways for each cluster were identified.

**分析得到什么**

得到 Mo-TAM cluster-level pathway programs。

**生物学解释**

pathway programs 为后续 Hypoxia-TAM 解释提供功能证据。

**证据如何推进**

分析从 gene signature 推进到 pathway-level functional annotation。

**下一步为什么出现**

下一步可以结合 marker 和 pathway evidence 判断是否存在 hypoxia-associated Mo-TAM state。

**解释边界**

GSVA 是通路富集/打分证据，不应写成直接功能实验。

**证据锚点**

- p.26；STAR Methods；`GSVA`：方法说明 MSigDB C2/C5、GSVA 参数和 core pathway 识别阈值。

**审查提醒**

- pathway annotation 是关联证据，不是功能因果。

#### C1_S07 Hypoxia-TAM state identification from marker and pathway evidence

- 连接：`C1_S06` -> `C1_S07` -> `END`
- 证据等级：`enrichment`
- Gold confidence：`medium`

**分析问题**

测试是否存在一个可被 marker/pathway evidence 支持的 hypoxia-associated Mo-TAM state。

**输入数据**

- Mo-TAM cluster markers
- Mo-TAM pathway programs

**为什么做这一步**

如果某个 Mo-TAM cluster 同时显示 hypoxia response genes、glycolysis 和 proangiogenic features，它可以作为后续空间定位和候选因子筛选对象。

**分析任务**

用 marker 和 pathway evidence 解释 Mo-TAM clusters，重点关注 hypoxia response、glycolysis 和 proangiogenic features。

**观察到的数据证据**

- Hypoxia-TAM cluster 上调 ADM、BNIP3、CSTB。
- 该 cluster 关联 glycolysis 和 proangiogenic features。

**分析得到什么**

一个 Mo-TAM cluster 被 marker/pathway evidence 区分为 hypoxia-associated state。

**生物学解释**

作者将该状态解释并命名为 Hypoxia-TAM。

**证据如何推进**

分析从 Mo-TAM functional annotation 推进到一个可命名、可映射、可筛选候选因子的细胞状态。

**下一步为什么出现**

下一步需要把 Hypoxia-TAM 映射回组织空间，测试它是否位于 peri-necrotic / hypoxic niche。

**解释边界**

Hypoxia-TAM 命名是 interpretation；marker/pathway evidence 仍是关联证据。

**证据锚点**

- p.5；Results；`ADM, BNIP3, and CSTB`：结果描述 Hypoxia-TAM cluster 上调 hypoxia response genes 并具有 glycolysis / proangiogenic features。

**审查提醒**

- 不要把 Hypoxia-TAM 命名写成因果证明。
- observed_evidence 必须和 biological_interpretation 分开。

### 从 Mo-TAM 状态到空间生态位定位

#### C2_S01 Public Visium preprocessing and image alignment

- 连接：`START` -> `C2_S01` -> `C2_S02`
- 证据等级：`preprocessing`
- Gold confidence：`medium`

**分析问题**

测试公共 hGBM Visium 数据是否能被整理为空间表达矩阵和图像对齐对象。

**输入数据**

- Public hGBM Visium spatial transcriptomics datasets
- Paired histology images

**为什么做这一步**

要把 scRNA 状态映射到组织，需要先得到可分析的 Visium count matrix，并使 spot positions 与 H&E 图像对齐。

**分析任务**

使用 SpaceRanger 将 reads 比对到 GRCh38-2020-A，生成每个样本的 mRNA count matrix，并将 Visium spot positions 与 paired histology images 对齐。

**观察到的数据证据**

- public hGBM Visium 数据被处理为 count matrices。
- Visium spot positions 与 paired histology images 对齐。

**分析得到什么**

得到后续 Seurat/Cell2location 可使用的空间表达矩阵和 spot-image alignment。

**生物学解释**

空间表达矩阵和 H&E 对齐让 scRNA 状态具备组织定位分析入口。

**证据如何推进**

分析从 scRNA-defined state 推进到 spatial transcriptomics data object。

**下一步为什么出现**

下一步需要对 spot 质量和 normalization 做处理，确保空间映射不受低质量 spots 影响。

**解释边界**

预处理本身不提供 Hypoxia-TAM 空间富集结论。

**证据锚点**

- p.27；STAR Methods；`SpaceRanger`：方法说明 public Visium 数据、SpaceRanger 比对、count matrix 生成和 H&E alignment。

**审查提醒**

- 不要把 SpaceRanger 预处理写成空间生态位发现。

#### C2_S02 Visium spot QC and normalization

- 连接：`C2_S01` -> `C2_S02` -> `C2_S03`
- 证据等级：`preprocessing`
- Gold confidence：`medium`

**分析问题**

测试哪些 hGBM spatial samples 和 spots 可用于后续空间映射。

**输入数据**

- SpaceRanger outputs
- Visium spots
- Paired images

**为什么做这一步**

为了让 Cell2location 和 region-level comparison 可靠，需要过滤异常 spots 并统一 normalization。

**分析任务**

使用 Seurat 处理 SpaceRanger outputs；过滤 counts、genes 和 mitochondrial percentage 异常 spots；用 SCTransform normalization/scaling/regression；排除两个图像质量差的 samples。

**观察到的数据证据**

- 低质量 Visium spots 被过滤。
- 两个低质量图像样本被排除。
- 最终 35 cases 进入后续分析。

**分析得到什么**

得到 QC 后的 hGBM spatial transcriptomic dataset。

**生物学解释**

这一步建立可用于 spatial mapping 的质量控制边界。

**证据如何推进**

分析从 raw/public spatial object 推进到 QC-normalized spatial analysis object。

**下一步为什么出现**

下一步可以用 scRNA-derived Mo-TAM signatures 建立 Cell2location reference。

**解释边界**

QC 后保留的 35 cases 仍依赖公开数据质量和作者处理流程。

**证据锚点**

- p.27；STAR Methods；`SCTransform`：方法列出 Visium spot 过滤阈值、SCTransform 回归变量、排除样本和最终 35 cases。

**审查提醒**

- spot QC 不是空间富集结果，只是后续映射前提。

#### C2_S03 Cell2location reference model construction

- 连接：`C2_S02` -> `C2_S03` -> `C2_S04`
- 证据等级：`spatial_mapping`
- Gold confidence：`medium`

**分析问题**

测试 scRNA-defined Mo-TAM states 是否能作为 spatial decomposition 的 reference。

**输入数据**

- Annotated Mo-TAM clusters from scRNA-seq
- Mo-TAM signatures

**为什么做这一步**

Cell2location 需要从已注释 Mo-TAM clusters 建 reference signature model，再用于 spatial decomposition。

**分析任务**

用 hGBM scRNA-seq 中已注释 Mo-TAM clusters 估计 reference signature；donor ID 作为 batch category，训练 Cell2location model。

**观察到的数据证据**

- Cell2location reference signature model was built from annotated Mo-TAM clusters.
- donor ID 被作为 batch category。

**分析得到什么**

得到用于 spatial decomposition 的 Mo-TAM reference signature model。

**生物学解释**

scRNA 定义的 Mo-TAM states 被转换为空间映射模型的 reference。

**证据如何推进**

分析从 scRNA state definition 推进到可用于 spot decomposition 的 reference model。

**下一步为什么出现**

下一步用 reference model 分解每个 spatial spot 的 Mo-TAM cluster proportion。

**解释边界**

reference model 质量依赖 scRNA annotation 和 batch handling。

**证据锚点**

- p.27；STAR Methods；`reference signature`：方法说明 Cell2location reference signature、negative binomial model 和训练参数。

**审查提醒**

- Cell2location reference 是映射模型，不等同于真实细胞计数。

#### C2_S04 Spatial spot-level Mo-TAM decomposition

- 连接：`C2_S03` -> `C2_S04` -> `C2_S05`
- 证据等级：`spatial_mapping`
- Gold confidence：`medium`

**分析问题**

测试 scRNA-defined Mo-TAM states 能否被投射到 spatial spots。

**输入数据**

- QC-normalized Visium count matrices
- Cell2location reference signature model

**为什么做这一步**

要比较不同组织区域中的 Hypoxia-TAM，需要先估计每个 spot 的 Mo-TAM cluster proportion。

**分析任务**

用 Cell2location reference signature model 分解 spatial transcriptomic mRNA counts，并估计每个 spot 中各 Mo-TAM cluster proportion。

**观察到的数据证据**

- 每个 spatial spot 获得 Mo-TAM cluster proportion estimates。
- Cell2location decomposition 使用明确参数。

**分析得到什么**

得到 spot-level Mo-TAM composition estimates。

**生物学解释**

Mo-TAM states 从 scRNA clusters 变成组织空间中的 spot-level abundance estimates。

**证据如何推进**

分析从 reference model 推进到 spatially resolved Mo-TAM composition。

**下一步为什么出现**

下一步需要把 spot-level composition 与 histology regions 对齐，判断空间生态位。

**解释边界**

spot-level proportion 是模型估计值，不是直接显微计数。

**证据锚点**

- p.27；STAR Methods；`decompose mRNA counts`：方法说明 Cell2location 分解 spatial mRNA counts 并估计每个 spot 的 Mo-TAM cluster proportion。

**审查提醒**

- 不要把 Cell2location proportion 当成直接观测的细胞数量。

#### C2_S05 Histology-region assignment to spatial spots

- 连接：`C2_S04` -> `C2_S05` -> `C2_S06`
- 证据等级：`spatial_mapping`
- Gold confidence：`medium`

**分析问题**

测试每个 spatial spot 是否能获得可比较的 histology region label。

**输入数据**

- H&E images
- Spatial spots
- Ivy hGBM histology categories

**为什么做这一步**

要测试空间生态位，需要将 H&E histology annotation 映射到每个 spatial spot。

**分析任务**

使用 Ivy hGBM 四类 histology regions，由 neuropathologists 在 H&E 上标注，并用 QuPath 导出 GeoJSON 后映射到 spatial spots。

**观察到的数据证据**

- spatial spots 被赋予 Ivy hGBM histology region labels。
- QuPath / GeoJSON 完成 H&E annotation 到 spot 的映射。

**分析得到什么**

得到带有 histology region labels 的 spatial spots。

**生物学解释**

组织学区域标签使 Mo-TAM spatial composition 可以按 niche 进行比较。

**证据如何推进**

分析从 spot-level composition 推进到 histology-aware spatial comparison。

**下一步为什么出现**

下一步可以计算每个 region 中 Mo-TAM cluster proportion 的均值并比较富集。

**解释边界**

histology annotation 包含人工判读，可能影响区域边界。

**证据锚点**

- p.27；STAR Methods；`GeoJSON`：方法说明 Ivy hGBM 四类 histology regions、neuropathologist annotation、QuPath 和 GeoJSON mapping。

**审查提醒**

- 区域标签是 histology assignment，不是分子机制证据。

#### C2_S06 Region-level Mo-TAM enrichment analysis

- 连接：`C2_S05` -> `C2_S06` -> `END`
- 证据等级：`association`
- Gold confidence：`medium`

**分析问题**

测试 Hypoxia-TAM 是否在 peri-necrotic region 中富集。

**输入数据**

- Spot-level Mo-TAM proportions
- Spot-level histology region labels

**为什么做这一步**

如果 Hypoxia-TAM 由 hypoxic / necrotic niche 塑造，它应在 peri-necrotic region 中显示更高 proportion。

**分析任务**

计算每个 histology region 内各 Mo-TAM cluster 的 Cell2location-computed proportion mean score，并用 ComplexHeatmap 展示 histology-transcriptome assignments。

**观察到的数据证据**

- Hypoxia-TAM preferentially localized in the peri-necrotic region。
- 其他 Mo-TAM clusters 在不同 regions 中呈现不同 spatial distributions。

**分析得到什么**

Hypoxia-TAM 获得 peri-necrotic spatial niche association。

**生物学解释**

作者将 Hypoxia-TAM 与 hGBM peri-necrotic / hypoxic niche 联系起来。

**证据如何推进**

分析从 scRNA-defined cell state 推进到 tissue niche-associated state。

**下一步为什么出现**

下一步可以问：这个 niche-associated Hypoxia-TAM 是否有与 hypoxia 和 vascular remodeling 相关的候选基因或通讯因子。

**解释边界**

空间富集是 association，不是 Hypoxia-TAM 导致坏死或血管异常的因果证据。

**证据锚点**

- p.27；STAR Methods；`mean score`：方法说明按 histological regions 计算每个 Mo-TAM cluster 的 Cell2location proportion mean score。
- p.5；Results；`preferentially localized`：结果报告 Hypoxia-TAM preferentially localized in the peri-necrotic region。

**审查提醒**

- 不能把 region enrichment 写成因果。

### 从 Hypoxia-TAM 到候选机制优先级排序

#### C3_S01 Hypoxia-associated gene set construction

- 连接：`START` -> `C3_S01` -> `C3_S02`
- 证据等级：`association`
- Gold confidence：`medium`

**分析问题**

测试哪些 genes 同时与 Hypoxia-TAM upregulation 和 hypoxia score 相关。

**输入数据**

- Hypoxia-TAM upregulated genes
- HARRIS_HYPOXIA gene set
- Hypoxia-TAM single-cell expression

**为什么做这一步**

候选机制不能只来自 cluster 名称，需要从 Hypoxia-TAM DEGs、hypoxia gene set 和 hypoxia score correlation 中筛选。

**分析任务**

定义 core HRGs，计算每个 Hypoxia-TAM cell 的 hypoxia score，用 Pearson correlation 找 top positive/negative correlated genes，并与 Hypoxia-TAM DEGs overlap 得到 HPGs/HNGs。

**观察到的数据证据**

- core HRGs、HPGs 和 HNGs 被构建。
- hypoxia score correlation 将候选 genes 与 Hypoxia-TAM 内部 hypoxia gradient 联系起来。

**分析得到什么**

得到 Hypoxia-TAM hypoxia-associated gene candidates。

**生物学解释**

这些 genes 被解释为 Hypoxia-TAM hypoxia-associated programs 的候选组成部分。

**证据如何推进**

分析从空间关联的 Hypoxia-TAM state 推进到 hypoxia-associated candidate gene set。

**下一步为什么出现**

下一步需要把这些候选 genes 组织成 interaction / functional network。

**解释边界**

correlation with hypoxia score 仍是关联证据，不是调控因果。

**证据锚点**

- p.26；STAR Methods；`Hypoxia-associated gene interaction network`：方法说明 HRGs、AddModuleScore、Pearson correlation、top genes 和 HPG/HNG overlap。

**审查提醒**

- 不要把 hypoxia score correlation 写成基因调控因果。

#### C3_S02 Functional network annotation of hypoxia-associated genes

- 连接：`C3_S01` -> `C3_S02` -> `C3_S03`
- 证据等级：`network_support`
- Gold confidence：`medium`

**分析问题**

测试 hypoxia-associated genes 是否形成可解释的 functional interaction network。

**输入数据**

- Core HRGs
- HPGs
- HNGs

**为什么做这一步**

为了解释 Hypoxia-TAM 程序，需要将候选 genes 放入 interaction 和 functional annotation 框架。

**分析任务**

使用 STRING 预测 core HRGs 与 HPGs/HNGs 的 interactions，用 DAVID 做 clustering / functional annotation，并用 Cytoscape 可视化。

**观察到的数据证据**

- Hypoxia-associated genes 被组织成 interaction network。
- DAVID 提供 functional annotation / clustering。

**分析得到什么**

得到 Hypoxia-TAM hypoxia-associated gene interaction network。

**生物学解释**

网络注释帮助解释 Hypoxia-TAM 与 hypoxia adaptation、niche remodeling 等功能程序的关系。

**证据如何推进**

分析从 candidate gene list 推进到 functionally organized network。

**下一步为什么出现**

下一步可以进一步推断调控这些 Hypoxia-TAM programs 的 TF/regulon。

**解释边界**

STRING/DAVID/Cytoscape 是网络和功能注释证据，不是直接实验验证。

**证据锚点**

- p.26；STAR Methods；`STRING database`：方法说明 STRING interaction、DAVID clustering/function annotation 和 Cytoscape visualization。

**审查提醒**

- 网络预测不能写成直接物理互作证明。

#### C3_S03 SCENIC regulon analysis

- 连接：`C3_S02` -> `C3_S03` -> `C3_S04`
- 证据等级：`network_support`
- Gold confidence：`medium`

**分析问题**

测试 Mo-TAM clusters 是否具有不同 TF regulon activity，哪些 TF 可能关联 Hypoxia-TAM signature。

**输入数据**

- Mo-TAM scRNA-seq expression matrix
- Mo-TAM cells from necrotic hGBM cases

**为什么做这一步**

要提出上游调控候选，需要在 Mo-TAM single-cell expression 中推断 TF-target regulons 并评分 regulon activity。

**分析任务**

从 hGBM-IDHwt-7 和 hGBM-IDHwt-17 抽取 1,000 Mo-TAMs，用 GENIE3、RcisTarget 和 AUCell 执行 SCENIC regulon analysis。

**观察到的数据证据**

- 282 regulons were identified。
- 每个细胞获得 regulon activity scores。

**分析得到什么**

得到 Mo-TAM regulon activity landscape。

**生物学解释**

SCENIC 结果用于优先考虑 Hypoxia-TAM signature 相关 TF programs。

**证据如何推进**

分析从 gene-level network 推进到 TF/regulon-level prioritization。

**下一步为什么出现**

下一步可以结合 cell-cell interaction 或 secreted factor screening 寻找 Hypoxia-TAM 影响其他细胞的候选通讯因子。

**解释边界**

SCENIC 是计算推断，不是 TF 直接调控验证。

**证据锚点**

- p.26；STAR Methods；`SCENIC algorithm`：方法说明 GENIE3、RcisTarget、AUCell 和 282 regulons。
- p.8；Results；`SCENIC`：结果提到用 SCENIC 筛选 potential TFs regulating Hypoxia-TAM signature。

**审查提醒**

- SCENIC regulon activity 不能写成已验证 TF binding。

#### C3_S04 EC-Mo-TAM ligand-receptor interaction analysis

- 连接：`C3_S03` -> `C3_S04` -> `C3_S05`
- 证据等级：`network_support`
- Gold confidence：`medium`

**分析问题**

测试 Hypoxia-TAM / Mo-TAM clusters 是否具有与 ECs 的候选 ligand-receptor communication。

**输入数据**

- ECs in hGBM scRNA-seq
- Mo-TAM clusters in hGBM scRNA-seq

**为什么做这一步**

如果 Hypoxia-TAM 影响血管相关状态，它可能通过 ligand-receptor interaction 与 ECs 通讯。

**分析任务**

使用 CellPhoneDB 分析 ECs 与 Mo-TAM clusters 之间的 intercellular interactions，计算 ligand/receptor average expression 和 cell specificity likelihood。

**观察到的数据证据**

- EC 与 Mo-TAM clusters 的 ligand-receptor candidate interactions 被计算。
- 每个 ligand-receptor pair 有 average expression / specificity likelihood 框架。

**分析得到什么**

得到 EC-Mo-TAM candidate communication map。

**生物学解释**

CellPhoneDB 为从 Hypoxia-TAM 状态转向 endothelial-related candidate mediators 提供计算候选。

**证据如何推进**

分析从 intracellular state programs 推进到 intercellular communication candidates。

**下一步为什么出现**

下一步可与 secreted protein / hypoxia response / Hypoxia-TAM signature 交集筛选结合，优先级排序具体候选因子。

**解释边界**

CellPhoneDB 是 ligand-receptor 计算推断，不是直接分泌或受体结合验证。

**证据锚点**

- p.26；STAR Methods；`CellPhoneDB`：方法说明 ECs 与 Mo-TAM clusters 的 CellPhoneDB ligand-receptor interaction analysis。

**审查提醒**

- CellPhoneDB 不能当作直接物理互作证据。

#### C3_S05 ADM candidate prioritization from Hypoxia-TAM secreted factors

- 连接：`C3_S04` -> `C3_S05` -> `END`
- 证据等级：`candidate_prioritization`
- Gold confidence：`medium`

**分析问题**

测试是否存在一个由 Hypoxia-TAM 表达、具备分泌属性、且与 hypoxia response 相连的优先候选。

**输入数据**

- Hypoxia-TAM signature genes
- Human secreted protein genes
- Hypoxia response gene set

**为什么做这一步**

如果要提出 Hypoxia-TAM-derived mediator，应同时满足 Hypoxia-TAM signature、secreted protein 和 hypoxia response 三类条件。

**分析任务**

交叉筛选 Hypoxia-TAM signature genes、human genes encoding secreted proteins 和 hypoxia response gene set。

**观察到的数据证据**

- ADM 是 Hypoxia-TAM signature genes、secreted protein genes 和 hypoxia response gene set 交集筛选得到的 only candidate。

**分析得到什么**

ADM 被计算优先级排序为文章后续验证的候选因子。

**生物学解释**

作者将 ADM 作为 Hypoxia-TAM-derived factor 进入后续机制实验验证。

**证据如何推进**

分析从 Hypoxia-TAM state / niche association 推进到一个可被文章后续验证链路承接的 candidate mediator。

**下一步为什么出现**

后续验证可以作为文章整体逻辑上下文记录，但不属于 Agent 可执行的数据分析方法路径。

**解释边界**

ADM candidate prioritization 不是因果证明；因果性来自文章后续非数据分析验证。

**证据锚点**

- p.8；Results；`ADM as the only candidate`：结果描述交集筛选 Hypoxia-TAM signature genes、secreted protein genes 和 hypoxia response gene set，ADM 为唯一候选。

**审查提醒**

- 不要把 ADM only candidate 写成 ADM 已导致血管异常。
- 文章后续验证可以作为 context，但不能污染 Agent 可复用的方法递进路径。

## Article Context After Analysis

这些内容属于文章整体逻辑链路的一部分，但不属于 Agent 可复用的数据分析方法递进路径：

- Adm cKO xenograft 用于测试 ADM loss-of-function 必要性；这是文章整体链路中的后续验证，不属于 Agent 可执行的数据分析方法路径。
- Endothelial assay 和 AMA rescue 用于验证 ADM/CRLR/VE-cadherin 机制；它们可作为文章上下文，不作为可复用分析方法 step。
- AMA + dabrafenib delivery / survival readouts 是转化前实验验证；它说明文章如何支持候选因子，但不能写成计算分析结论。
