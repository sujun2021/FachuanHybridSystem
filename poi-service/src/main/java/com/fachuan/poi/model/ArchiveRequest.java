package com.fachuan.poi.model;

import java.util.List;

/**
 * Archive document generation request.
 * Contains all data needed for 案卷封面, 结案归档登记表, 卷内目录.
 */
public class ArchiveRequest {

    // Basic case info
    private String caseName;
    private String caseType; // "刑事" / "民事" / "行政"
    private String caseNumber; // e.g. "(2006)粤0604刑初155号"
    private String causeOfAction; // 案由
    private String courtName; // 管辖法院
    private String caseStage; // 案件阶段
    private String trialResult; // 审理结果
    private String oaCaseNumber; // OA编号

    // Party info
    private String ourPartyName; // 我方当事人
    private String opposingPartyName; // 对方当事人
    private String leadLawyer; // 主办律师

    // Dates
    private String startDate;
    private String archiveDate;
    private String year;

    // Contract info
    private String contractName;
    private String contractType;

    // Archive materials
    private List<ArchiveItem> archiveItems;

    // Catalog entries
    private List<CatalogEntry> catalogEntries;

    // ── Getters/Setters ──

    public String getCaseName() { return caseName; }
    public void setCaseName(String caseName) { this.caseName = caseName; }
    public String getCaseType() { return caseType; }
    public void setCaseType(String caseType) { this.caseType = caseType; }
    public String getCaseNumber() { return caseNumber; }
    public void setCaseNumber(String caseNumber) { this.caseNumber = caseNumber; }
    public String getCauseOfAction() { return causeOfAction; }
    public void setCauseOfAction(String causeOfAction) { this.causeOfAction = causeOfAction; }
    public String getCourtName() { return courtName; }
    public void setCourtName(String courtName) { this.courtName = courtName; }
    public String getCaseStage() { return caseStage; }
    public void setCaseStage(String caseStage) { this.caseStage = caseStage; }
    public String getTrialResult() { return trialResult; }
    public void setTrialResult(String trialResult) { this.trialResult = trialResult; }
    public String getOaCaseNumber() { return oaCaseNumber; }
    public void setOaCaseNumber(String oaCaseNumber) { this.oaCaseNumber = oaCaseNumber; }
    public String getOurPartyName() { return ourPartyName; }
    public void setOurPartyName(String ourPartyName) { this.ourPartyName = ourPartyName; }
    public String getOpposingPartyName() { return opposingPartyName; }
    public void setOpposingPartyName(String v) { this.opposingPartyName = v; }
    public String getLeadLawyer() { return leadLawyer; }
    public void setLeadLawyer(String leadLawyer) { this.leadLawyer = leadLawyer; }
    public String getStartDate() { return startDate; }
    public void setStartDate(String startDate) { this.startDate = startDate; }
    public String getArchiveDate() { return archiveDate; }
    public void setArchiveDate(String archiveDate) { this.archiveDate = archiveDate; }
    public String getYear() { return year; }
    public void setYear(String year) { this.year = year; }
    public String getContractName() { return contractName; }
    public void setContractName(String contractName) { this.contractName = contractName; }
    public String getContractType() { return contractType; }
    public void setContractType(String contractType) { this.contractType = contractType; }
    public List<ArchiveItem> getArchiveItems() { return archiveItems; }
    public void setArchiveItems(List<ArchiveItem> archiveItems) { this.archiveItems = archiveItems; }
    public List<CatalogEntry> getCatalogEntries() { return catalogEntries; }
    public void setCatalogEntries(List<CatalogEntry> catalogEntries) { this.catalogEntries = catalogEntries; }

    // ── Inner classes ──

    public static class ArchiveItem {
        private String name;
        private String pages;
        private String note;

        public ArchiveItem() {}
        public ArchiveItem(String name, String pages, String note) {
            this.name = name;
            this.pages = pages;
            this.note = note;
        }

        public String getName() { return name; }
        public void setName(String name) { this.name = name; }
        public String getPages() { return pages; }
        public void setPages(String pages) { this.pages = pages; }
        public String getNote() { return note; }
        public void setNote(String note) { this.note = note; }
    }

    public static class CatalogEntry {
        private String sequenceNumber;
        private String materialName;
        private String pageNumbers;

        public CatalogEntry() {}
        public CatalogEntry(String seq, String name, String pages) {
            this.sequenceNumber = seq;
            this.materialName = name;
            this.pageNumbers = pages;
        }

        public String getSequenceNumber() { return sequenceNumber; }
        public void setSequenceNumber(String v) { this.sequenceNumber = v; }
        public String getMaterialName() { return materialName; }
        public void setMaterialName(String materialName) { this.materialName = materialName; }
        public String getPageNumbers() { return pageNumbers; }
        public void setPageNumbers(String pageNumbers) { this.pageNumbers = pageNumbers; }
    }
}
