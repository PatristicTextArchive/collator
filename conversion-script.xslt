<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="2.0" xpath-default-namespace="http://www.tei-c.org/ns/1.0" xmlns:tei="http://www.tei-c.org/ns/1.0">

  <xsl:variable name="witness-id"><xsl:value-of select="/TEI/teiHeader/fileDesc/sourceDesc/msDesc/msIdentifier/@xml:id"/></xsl:variable>

  <xsl:output method="text" indent="yes"/>
  <xsl:strip-space elements="div"/>


  <xsl:template match="/">
    {witness:<xsl:value-of select="$witness-id"/>}
    {content:<xsl:apply-templates select="//body"/>}
    <!-- {content:<xsl:apply-templates select="//body//div[@n='6']"/>} -->
  </xsl:template>

  <xsl:template match="text()">
        <xsl:analyze-string select="." regex="ϗ">
            <xsl:matching-substring>
              <xsl:text>(καὶ)</xsl:text>
            </xsl:matching-substring>
            <xsl:non-matching-substring>
                <xsl:value-of select="."/>
            </xsl:non-matching-substring>
        </xsl:analyze-string>
  </xsl:template>

  <!--<xsl:template match="div[@subtype='chapter']">
    <xsl:text>&#xa;{ch.=</xsl:text><xsl:value-of select="./@n"/><xsl:text>}
    </xsl:text>
   <xsl:apply-templates/>
  </xsl:template>

  <xsl:template match="div[@subtype='section']">
    <xsl:text>&#xa;{s.=</xsl:text><xsl:value-of select="./@n"/><xsl:text>}
    </xsl:text>
   <xsl:apply-templates/>
  </xsl:template>-->

  <xsl:template match="div//head"><xsl:text> </xsl:text><xsl:apply-templates/><xsl:text> </xsl:text></xsl:template>

  <xsl:template match="p">
    <xsl:text>&#xa;</xsl:text>
    <xsl:apply-templates />
    <xsl:text>&#xa;</xsl:text>
  </xsl:template>

  <xsl:template match="lb">
    <xsl:choose>
      <xsl:when test="@break='no'">
        <xsl:text></xsl:text></xsl:when>
      <xsl:otherwise><xsl:text> </xsl:text></xsl:otherwise>
    </xsl:choose>
  </xsl:template>


  <xsl:template match="unclear">{unclear–<xsl:apply-templates/>}</xsl:template>

  <xsl:template match="hi">
    <xsl:if test="@rend='initial'">
    <xsl:text>{initial=</xsl:text>
      <xsl:apply-templates/>
      <xsl:text>}</xsl:text>
    </xsl:if>
    <xsl:if test="@rend='ekthesis'">
      <xsl:text>{ekthesis=</xsl:text>
      <xsl:apply-templates/>
      <xsl:text>}</xsl:text>
    </xsl:if>
    <xsl:if test="@rend='overline'">
      <xsl:text>{overline=</xsl:text>
      <xsl:apply-templates/>
      <xsl:text>}</xsl:text>
    </xsl:if>
    <xsl:if test="@rend='rubricated'">
      <xsl:apply-templates/>
    </xsl:if>
  </xsl:template>


  <xsl:template match="pb">
    <xsl:choose>
      <xsl:when test="@break='no'">
        <xsl:text>{f=</xsl:text><xsl:value-of select="./@n"/>}</xsl:when>
      <xsl:otherwise><xsl:text> </xsl:text>{f=<xsl:value-of select="./@n"/>}<xsl:text> </xsl:text></xsl:otherwise>
    </xsl:choose>
  </xsl:template>

  <xsl:template match="del">
    <xsl:text>{del=</xsl:text>
    <xsl:apply-templates/><xsl:text>–</xsl:text><xsl:value-of select="@rend"/>
    <xsl:text>}</xsl:text>
  </xsl:template>

  <xsl:template match="add">
    <xsl:text>{add=</xsl:text>
    <xsl:apply-templates/><xsl:text>–</xsl:text><xsl:value-of select="@place"/>
    <xsl:text>}</xsl:text>
  </xsl:template>
  
  <xsl:template match="gap">
    <xsl:variable name="count" select="@quantity"/>
    <xsl:variable name="unit" select="@unit"/>
    
    <xsl:for-each select="1 to $count">
      <xsl:choose>
        <xsl:when test="$unit='line'">
          <xsl:text>{</xsl:text><xsl:value-of select="$unit"/><xsl:text>}</xsl:text>
          <xsl:text> </xsl:text>
        </xsl:when>
        <xsl:when test="$unit='word'">
          <xsl:text>{</xsl:text><xsl:value-of select="$unit"/><xsl:text>}</xsl:text>
          <xsl:text> </xsl:text>
        </xsl:when>
        <xsl:when test="$unit='character'">
          <xsl:text>{c}</xsl:text>
        </xsl:when>
      </xsl:choose>    
    </xsl:for-each>
  </xsl:template>

  <xsl:template match="choice">
		<xsl:text>(</xsl:text>
		<xsl:value-of select="tei:expan"/>
		<xsl:text>)</xsl:text>
	</xsl:template>

<xsl:template match="g">
<!--   <xsl:if test="@type='doubled_diple'">
    <xsl:text>» </xsl:text>
  </xsl:if>
  <xsl:if test="@type='diple'">
    <xsl:text>› </xsl:text>
  </xsl:if>
  <xsl:if test="@type='paragraphos'">
    <xsl:text>– </xsl:text>
  </xsl:if> -->
</xsl:template>

<xsl:template match="num">
  <xsl:text></xsl:text><xsl:value-of select="."/><xsl:text></xsl:text>
</xsl:template>

<xsl:template match="note">
</xsl:template>

<xsl:template match="stamp">
</xsl:template>

</xsl:stylesheet>
