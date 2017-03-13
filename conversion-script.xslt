<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="2.0" xpath-default-namespace="http://www.tei-c.org/ns/1.0" xmlns:tei="http://www.tei-c.org/ns/1.0">

  <!-- Variables from XML teiHeader -->
  <xsl:variable name="title"><xsl:value-of select="/TEI/teiHeader/fileDesc/titleStmt/title"/></xsl:variable>
  <xsl:variable name="author"><xsl:value-of select="/TEI/teiHeader/fileDesc/titleStmt/author"/></xsl:variable>
  <xsl:variable name="witness-id"><xsl:value-of select="/TEI/teiHeader/fileDesc/sourceDesc/listWit/witness/@xml:id"/></xsl:variable>

  <!-- BEGIN: Document configuration -->
  <!-- Variables -->
  <xsl:variable name="app_entry_separator">;</xsl:variable>
  <xsl:variable name="starts_on" select="/TEI/text/front/div/pb"/>

  <!-- Apparatus switches -->
  <xsl:variable name="ignoreSpellingVariants" select="true()"/>
  <xsl:variable name="ignoreInsubstantialEntries" select="true()"/>
  <xsl:variable name="positiveApparatus" select="false()"/>
  <xsl:variable name="apparatusNumbering" select="false()"/>

  <!-- Diplomatic switches -->
  <xsl:variable name="includeLinebreaks" select="false()"/>
  <xsl:variable name="normalizeSpelling" select="true()"/>
  <!-- END: Document configuration -->

  <!-- Begin conversion templates -->

  <xsl:output method="text" indent="no"/>
  <xsl:strip-space elements="div"/>
  <xsl:template match="text()">
      <xsl:value-of select="replace(., '\s+', ' ')"/>
  </xsl:template>

  <xsl:template match="/">
    {witness:<xsl:value-of select="$witness-id"/>}
    {content:<xsl:apply-templates select="//body"/>}
  </xsl:template>


  <xsl:template match="div//head"><xsl:apply-templates/></xsl:template>
  <xsl:template match="p">
    <xsl:apply-templates />
  </xsl:template>

  <!-- Normalization template -->
  <xsl:template match="choice/orig">
    <xsl:choose>
      <xsl:when test="$normalizeSpelling">
        <xsl:value-of select="./reg"/>
      </xsl:when>
      <xsl:otherwise>
        <xsl:value-of select="./orig"/>
      </xsl:otherwise>
    </xsl:choose>
  </xsl:template>

  <xsl:template match="unclear">{unclear:<xsl:apply-templates/>}</xsl:template>
  <xsl:template match="pb">{pb:@ed <xsl:value-of select="translate(./@ed, '#', '')"/> @n <xsl:value-of select="./@n"/></xsl:template>
  <xsl:template match="supplied">{supplied:<xsl:apply-templates/>}</xsl:template>
  <xsl:template match="secl">{secluded:<xsl:apply-templates/>}</xsl:template>
  <xsl:template match="del">{del:<xsl:apply-templates/>}</xsl:template>
  <xsl:template match="add">{add:<xsl:apply-templates/>, <xsl:value-of select="@place"/>}</xsl:template>
  <xsl:template match="cit[bibl]">
    <xsl:choose>
      <xsl:when test="./quote">
        <xsl:text>"</xsl:text>
        <xsl:apply-templates select="quote"/>
        <xsl:text>"</xsl:text>
      </xsl:when>
      <xsl:when test="./ref">
        <xsl:apply-templates select="ref"/>
      </xsl:when>
    </xsl:choose>
  </xsl:template>
  <xsl:template match="ref[bibl]">
    <xsl:apply-templates select="seg"/>
  </xsl:template>
  <xsl:template match="ref"><xsl:apply-templates/></xsl:template>

</xsl:stylesheet>
