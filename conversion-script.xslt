<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="2.0" xpath-default-namespace="http://www.tei-c.org/ns/1.0" xmlns:tei="http://www.tei-c.org/ns/1.0">

  <xsl:variable name="witness-id"><xsl:value-of select="/TEI/teiHeader/fileDesc/sourceDesc/listWit/witness/@xml:id"/></xsl:variable>
  <xsl:variable name="normalizeSpelling" select="true()"/>

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
    <xsl:text>&#xa;</xsl:text>
    <xsl:apply-templates />
    <xsl:text>&#xa;</xsl:text>
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
